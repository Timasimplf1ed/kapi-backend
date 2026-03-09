"""
KAPI ERP — Telegram Bot
/qoldiq, /kassa, /dilerlar
"""

import os, requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "BU_YERGA_TOKENNI_QOY")
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000")

def fmt(n):
    return f"${round(n):,}".replace(",", " ")

# ── /start ────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚪 *KAPI ERP Bot*\n\n"
        "Buyruqlar:\n"
        "📦 /qoldiq — Tovar qoldiqlari\n"
        "💰 /kassa — Kassa balansi\n"
        "👥 /dilerlar — Dilerlar va qarz\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /qoldiq ───────────────────────────────────────────────────
async def qoldiq(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{SERVER_URL}/api/qoldiq", timeout=10)
        items = r.json()
    except Exception as e:
        await update.message.reply_text(f"❌ Server xatosi: {e}")
        return

    if not items:
        await update.message.reply_text("📦 Tovarlar yo'q")
        return

    lines = ["📦 *Tovar qoldiqlari:*\n"]
    for item in items:
        qty = item["qty"]
        if qty == 0:
            icon = "🔴"
        elif qty < 5:
            icon = "🟡"
        else:
            icon = "🟢"
        lines.append(f"{icon} {item['name']} — *{qty} шт.*")
        lines.append(f"   _{item['zavod']}_")

    # Qisqa statistika
    nol  = sum(1 for i in items if i["qty"] == 0)
    kam  = sum(1 for i in items if 0 < i["qty"] < 5)
    yetarli = sum(1 for i in items if i["qty"] >= 5)
    lines.append(f"\n🟢 Yetarli: {yetarli}  🟡 Kam: {kam}  🔴 Tugagan: {nol}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── /kassa ────────────────────────────────────────────────────
async def kassa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{SERVER_URL}/api/kassa", timeout=10)
        b = r.json()
    except Exception as e:
        await update.message.reply_text(f"❌ Server xatosi: {e}")
        return

    jami = b.get("nal", 0) + b.get("plastik", 0) + b.get("hisob", 0)
    text = (
        "💰 *Kassa balansi:*\n\n"
        f"💵 Nalichnye:  *{fmt(b.get('nal', 0))}*\n"
        f"💳 Plastik:    *{fmt(b.get('plastik', 0))}*\n"
        f"🏦 Hisob raqam: *{fmt(b.get('hisob', 0))}*\n"
        f"\n📊 Jami: *{fmt(jami)}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /dilerlar ─────────────────────────────────────────────────
async def dilerlar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{SERVER_URL}/api/dilerlar", timeout=10)
        items = r.json()
    except Exception as e:
        await update.message.reply_text(f"❌ Server xatosi: {e}")
        return

    if not items:
        await update.message.reply_text("👥 Dilerlar yo'q")
        return

    lines = ["👥 *Dilerlar va qarzdorlik:*\n"]
    for d in items:
        debt = d["debt"]
        icon = "🔴" if debt > 0 else "🟢"
        lines.append(f"{icon} *{d['name']}*")
        if d.get("phone"):
            lines.append(f"   📱 {d['phone']}")
        lines.append(f"   Sotilgan: {fmt(d['bought'])}")
        lines.append(f"   To'langan: {fmt(d['paid'])}")
        if debt > 0:
            lines.append(f"   ❗ Qarz: *{fmt(debt)}*")
        else:
            lines.append(f"   ✅ Qarz yo'q")
        lines.append("")

    jami_qarz = sum(d["debt"] for d in items if d["debt"] > 0)
    lines.append(f"💸 Jami qarz: *{fmt(jami_qarz)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── MAIN ──────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("qoldiq",   qoldiq))
    app.add_handler(CommandHandler("kassa",    kassa))
    app.add_handler(CommandHandler("dilerlar", dilerlar))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
