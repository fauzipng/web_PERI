
from pathlib import Path
import joblib
from flask import Flask, jsonify, request

MODEL_PATH = Path(__file__).resolve().parent / "nb_sentimen.joblib"
model = joblib.load(MODEL_PATH)
app = Flask(__name__)


@app.after_request
def cors(resp):
    # Izinkan halaman admin (Live Server :5500 atau file lokal) memanggil API ini.
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


@app.get("/api/health")
def health():
    return jsonify(status="ok", kelas=list(model.classes_))


@app.route("/api/sentimen", methods=["POST", "OPTIONS"])
def sentimen():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(force=True, silent=True) or {}
    pesan = data.get("pesan")
    if isinstance(pesan, str):
        pesan = [pesan]
    if not isinstance(pesan, list) or not all(isinstance(t, str) for t in pesan):
        return jsonify(error="'pesan' harus berupa teks atau daftar teks"), 400
    if not pesan:
        return jsonify(hasil=[])
    hasil = []
    for t, p in zip(pesan, model.predict_proba(pesan)):
        i = int(p.argmax())
        hasil.append({"label": str(model.classes_[i]), "skor": round(float(p[i]), 3)})
    return jsonify(hasil=hasil, model="naive_bayes")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)