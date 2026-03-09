"""
KAPI ERP — Backend Server
Flask API: ERP dan ma'lumot oladi, botga beradi
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os

app = Flask(__name__)
CORS(app)  # ERP brauzerdan so'rov yuborishi uchun

DATA_FILE = "data.json"

# ── Ma'lumotlarni yuklash / saqlash ──────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "tovary": [], "fury": [], "sklad": {},
        "dillers": [], "orders": [], "vozvraty": [],
        "payments": [], "rashody": [], "menedjerlar": [],
        "nextId": {"tovar":1,"fura":1,"diller":1,"order":1,
                   "vozvrat":1,"payment":1,"rashod":1,"menedjer":1}
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── ERP → Server: ma'lumotlarni yuklash ──────────────────────
@app.route("/api/sync", methods=["POST"])
def sync():
    """ERP butun DB ni yuboradi, server saqlaydi"""
    db = request.get_json()
    if not db:
        return jsonify({"error": "Ma'lumot yo'q"}), 400
    save_data(db)
    return jsonify({"ok": True, "message": "Saqlandi"})

@app.route("/api/sync", methods=["GET"])
def sync_get():
    """ERP server dan ma'lumot oladi"""
    return jsonify(load_data())

# ── Bot uchun API endpointlar ─────────────────────────────────
@app.route("/api/qoldiq", methods=["GET"])
def qoldiq():
    """Tovar qoldiqlari"""
    db = load_data()
    result = []
    for t in db.get("tovary", []):
        sk = db.get("sklad", {}).get(str(t["id"]), {"qty": 0})
        result.append({
            "name":  t["name"],
            "zavod": t["zavod"],
            "qty":   sk.get("qty", 0)
        })
    result.sort(key=lambda x: x["qty"])
    return jsonify(result)

@app.route("/api/kassa", methods=["GET"])
def kassa():
    """Kassa balanslari"""
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
def dilerlar():
    """Dilerlar va qarzdorlik"""
    db = load_data()
    result = []
    for d in db.get("dillers", []):
        did = d["id"]
        bought   = sum(o["total"] for o in db.get("orders", [])   if o["dillerId"] == did)
        returned = sum(v["total"] for v in db.get("vozvraty", []) if v["dillerId"] == did)
        paid     = sum(p["amount"] for p in db.get("payments", []) if p["dillerId"] == did)
        debt     = bought - paid - returned
        result.append({
            "name":   d["name"],
            "phone":  d.get("phone", ""),
            "bought": bought,
            "paid":   paid,
            "debt":   debt
        })
    result.sort(key=lambda x: x["debt"], reverse=True)
    return jsonify(result)

# ── Health check ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "KAPI ERP Server ishlayapti ✅"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
