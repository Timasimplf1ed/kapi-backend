"""
KAPI ERP — Server + Bot (bitta fayl)
Flask API + Telegram Bot birga ishlaydi
"""

import os, json, threading, requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)
CORS(app)

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000")
DATA_FILE  = "data.json"

# ── Ma'lumotlar ───────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "tovary":[], "fury":[], "sklad":{}, "dillers":[],
        "orders":[], "vozvraty":[], "payments":[], "rashody":[], "menedjerlar":[],
        "nextId":{"tovar":1,"fura":1,"diller":1,"order":1,"vozvrat":1,"payment":1,"rashod":1,"menedjer":1}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fmt(n):
    return "$" + f"{round(n):,}".replace(",", " ")

# ── Flask API ─────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "KAPI ERP ishlayapti"})

@app.route("/api/sync", methods=["POST"])
def sync_post():
    db = request.get_json()
    if not db:
        return jsonify({"error": "Malumot yoq"}), 400
    save_data(db)
    return jsonify({"ok": True, "message": "Saqlandi"})

@app.route("/api/sync", methods=["GET"])
def sync_get():
    return jsonify(load_data())

@app.route("/api/qoldiq", methods=["GET"])
def qoldiq_api():
    db = load_data()
    result = []
    for t in db.get("tovary", []):
        sk = db.get("sklad", {}).get(str(t["id"]), {"qty": 0})
        result.append({"name": t["name"], "zavod": t["zavod"], "qty": sk.get("qty", 0)})
    result.sort(key=lambda x: x["qty"])
    return jsonify(result)

@app.route("/api/kassa", methods=["GET"])
def kassa_api():
    db = load_data()
    b = {"nal": 0, "plastik": 0, "hisob": 0}
    for p in db.get("payments", []):
        m = p.get("method", "nal")
        b[m] = b.get(m, 0) + p.get("amount", 0)
    for r in db.get("rashody", []):
        k = r.get("kassa", "nal")
        b[k] = b.get(k, 0) - r.get("amount", 0)
    return jsonify(b)

@app.route("/api/dilerlar", methods=["GET"])
def dilerlar_api():
    db = load_data()
    result = []
    for d in db.get("dillers", []):
        did = d["id"]
        bought   = sum(o["total"] for o in db.get("orders", [])   if o["dillerId"] == did)
        returned = sum(v["total"] for v in db.get("vozvraty", []) if v["dillerId"] == did)
        paid     = sum(p["amount"] for p in db.get("payments", []) if p["dillerId"] == did)
        result.append({"name": d["name"], "phone": d.get("phone",""), "bought": bought, "paid": paid, "debt": bought - paid - returned})
    result.sort(key=lambda x: x["debt"], reverse=True)
    return jsonify(result)

# ── Telegram Bot ──────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "KAPI ERP Bot\n\n"
        "Buyruqlar:\n"
        "/qoldiq - Tovar qoldiqlari\n"
        "/kassa - Kassa balansi\n"
        "/dilerlar - Dilerlar va qarz\n"
    )
    await update.message.reply_text(text)

async def cmd_qoldiq(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{SERVER_URL}/api/qoldiq", timeout=10)
        items = r.json()
    except Exception as e:
        await update.message.reply_text(f"Xato: {e}"); return

    if not items:
        await update.message.reply_text("Tovarlar yoq"); return

    lines = ["Tovar qoldiqlari:\n"]
    for item in items:
        qty  = item["qty"]
        icon = "🔴" if qty == 0 else "🟡" if qty < 5 else "🟢"
        lines.append(f"{icon} {item['name']} ({item['zavod']}) — {qty} sht")

    nol = sum(1 for i in items if i["qty"] == 0)
    kam = sum(1 for i in items if 0 < i["qty"] < 5)
    yet = sum(1 for i in items if i["qty"] >= 5)
    lines.append(f"\nYetarli: {yet}  Kam: {kam}  Tugagan: {nol}")
    await update.message.reply_text("\n".join(lines))

async def cmd_kassa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{SERVER_URL}/api/kassa", timeout=10)
        b = r.json()
    except Exception as e:
        await update.message.reply_text(f"Xato: {e}"); return

    jami = b.get("nal",0) + b.get("plastik",0) + b.get("hisob",0)
    text = (
        "Kassa balansi:\n\n"
        f"Nalichnye:   {fmt(b.get('nal',0))}\n"
        f"Plastik:     {fmt(b.get('plastik',0))}\n"
        f"Hisob raqam: {fmt(b.get('hisob',0))}\n"
        f"\nJami: {fmt(jami)}"
    )
    await update.message.reply_text(text)

async def cmd_dilerlar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{SERVER_URL}/api/dilerlar", timeout=10)
        items = r.json()
    except Exception as e:
        await update.message.reply_text(f"Xato: {e}"); return

    if not items:
        await update.message.reply_text("Dilerlar yoq"); return

    lines = ["Dilerlar va qarzdorlik:\n"]
    for d in items:
        icon = "🔴" if d["debt"] > 0 else "🟢"
        lines.append(f"{icon} {d['name']}")
        if d.get("phone"):
            lines.append(f"   Tel: {d['phone']}")
        lines.append(f"   Sotilgan:  {fmt(d['bought'])}")
        lines.append(f"   Tolangan: {fmt(d['paid'])}")
        lines.append(f"   Qarz: {fmt(d['debt'])}" if d["debt"] > 0 else "   Qarz yoq")
        lines.append("")

    jami = sum(d["debt"] for d in items if d["debt"] > 0)
    lines.append(f"Jami qarz: {fmt(jami)}")
    await update.message.reply_text("\n".join(lines))

def run_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN yoq, bot ishlamaydi")
        return
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start",    cmd_start))
    tg_app.add_handler(CommandHandler("qoldiq",   cmd_qoldiq))
    tg_app.add_handler(CommandHandler("kassa",    cmd_kassa))
    tg_app.add_handler(CommandHandler("dilerlar", cmd_dilerlar))
    print("Bot ishga tushdi!")
    tg_app.run_polling(stop_signals=None)

# ── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 5000))
    print(f"Server port {port} da ishga tushdi!")
    app.run(host="0.0.0.0", port=port)
