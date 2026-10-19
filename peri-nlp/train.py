
import json, sys
from pathlib import Path
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

from preprocessing import preprocess, bigram_analyzer, STEMMER_NAME

ROOT = Path(__file__).resolve().parent
DATA, MODEL, REPORT = ROOT / "dataset.csv", ROOT / "nb_sentimen.joblib", ROOT / "laporan.json"


def build(analyzer, alpha=1.0):
    return make_pipeline(TfidfVectorizer(analyzer=analyzer, min_df=2), MultinomialNB(alpha=alpha))


def main():
    df = pd.read_csv(DATA).dropna()
    X, y = df["teks"], df["label"]
    print(f"Data: {len(df)} baris | stemmer: {STEMMER_NAME}\n{y.value_counts().to_string()}\n")
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    # Bandingkan konfigurasi pada data latih (cross-validation), pilih terbaik
    skf = StratifiedKFold(5, shuffle=True, random_state=42)
    cands = {"unigram": preprocess, "unigram+bigram": bigram_analyzer}
    best, best_f1 = None, -1
    for name, an in cands.items():
        for a in (0.1, 0.5, 1.0):
            f1 = cross_val_score(build(an, a), Xtr, ytr, cv=skf, scoring="f1_macro").mean()
            print(f"CV F1-macro {name:15s} alpha={a:<4} -> {f1:.4f}")
            if f1 > best_f1:
                best, best_f1 = (name, a), f1
    print(f"\nTerpilih: {best} (CV F1-macro {best_f1:.4f})\n")

    model = build(cands[best[0]], best[1]).fit(Xtr, ytr)
    pred = model.predict(Xte)
    acc = accuracy_score(yte, pred)
    p, r, f, _ = precision_recall_fscore_support(yte, pred, average="macro")
    print("=== Naive Bayes (data uji, belum pernah dilihat model) ===")
    print(classification_report(yte, pred, digits=3))
    labels = sorted(y.unique())
    cm = confusion_matrix(yte, pred, labels=labels)
    print("Confusion matrix (baris=aktual, kolom=prediksi)", labels); print(cm, "\n")

    # Contoh kesalahan untuk dianalisis
    wrong = Xte[pred != yte].head(8)
    print("Contoh salah prediksi:")
    for t in wrong:
        print(" -", t[:110])

    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL)
    REPORT.write_text(json.dumps({
        "jumlah_data": len(df), "data_latih": len(Xtr), "data_uji": len(Xte), "konfigurasi": {"fitur": best[0], "alpha": best[1]},
        "cv_f1_macro": round(best_f1, 4), "accuracy": round(acc, 4), "precision_macro": round(p, 4),
        "recall_macro": round(r, 4), "f1_macro": round(f, 4), "confusion_matrix": {"label": labels, "nilai": cm.tolist()},
        "catatan": "Dilatih pada ulasan produk Tokopedia (PRDECT-ID); belum diuji pada data PERI."},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nModel: {MODEL}\nLaporan: {REPORT}")


if __name__ == "__main__":
    main()