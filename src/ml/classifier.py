import joblib
import re
from nltk.corpus import stopwords
import string

# Загружаем модель и векторизатор
model = joblib.load("src/ml/classifier.pkl")
vectorizer = joblib.load("src/ml/vectorizer.pkl")

stop_words = set(stopwords.words('russian')) | set(stopwords.words('english'))

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[' + string.punctuation + ']', ' ', text)
    tokens = [w for w in text.split() if w not in stop_words]
    return " ".join(tokens)

def predict(text):
    clean_text = preprocess_text(text)
    features = vectorizer.transform([clean_text])
    prob = model.predict_proba(features)[0][1]  # вероятность класса 1
    label = model.predict(features)[0]
    return label, prob
