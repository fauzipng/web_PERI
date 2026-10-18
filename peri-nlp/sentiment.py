"""Klasifikasi sentimen. Tahap 1: baseline lexicon (jalan tanpa data berlabel).
Tahap 2: Naive Bayes + TF-IDF (aktif setelah ada data berlabel di tabel sentimen_label)."""
from preprocessing import preprocess, NEGATIONS

# Kamus awal kecil: SEMENTARA, harus diperluas/divalidasi bersama PERI.
POS = {"bagus", "baik", "mantap", "bermanfaat", "manfaat", "puas", "senang", "membantu",
       "bantu", "ramah", "jelas", "mudah", "terima kasih", "inspiratif", "luar", "hebat"}
NEG = {"buruk", "jelek", "lambat", "susah", "sulit", "kecewa", "bingung", "lama",
       "error", "kurang", "mahal", "tidak jelas", "lelet"}


def lexicon_predict(text: str) -> dict:
    tokens = preprocess(text)
    score, hits = 0, 0
    for i, t in enumerate(tokens):
        val = 1 if t in POS else -1 if t in NEG else 0
        if not val:
            continue
        if i > 0 and tokens[i - 1] in NEGATIONS:
            val = -val
        score += val
        hits += 1
    norm = score / hits if hits else 0.0
    label = "positif" if norm > 0.2 else "negatif" if norm < -0.2 else "netral"
    return {"sentimen": label, "skor": round(norm, 3), "metode": "lexicon", "tokens": tokens}


class NaiveBayesSentiment:
    """Kerangka Naive Bayes. Belum dilatih: dipanggil setelah data berlabel tersedia."""

    def __init__(self):
        self.model = None

    def fit(self, texts, labels):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import make_pipeline
        self.model = make_pipeline(
            TfidfVectorizer(analyzer=preprocess), MultinomialNB(alpha=1.0))
        self.model.fit(texts, labels)
        return self

    def predict(self, text: str) -> dict:
        if self.model is None:
            raise RuntimeError("Model belum dilatih; gunakan lexicon_predict atau panggil fit().")
        proba = self.model.predict_proba([text])[0]
        classes = list(self.model.classes_)
        best = max(range(len(classes)), key=proba.__getitem__)
        return {"sentimen": classes[best], "skor": round(float(proba[best]), 3), "metode": "naive_bayes",
                "tokens": preprocess(text)}


def analyze(text: str, nb: "NaiveBayesSentiment | None" = None) -> dict:
    return nb.predict(text) if nb and nb.model else lexicon_predict(text)