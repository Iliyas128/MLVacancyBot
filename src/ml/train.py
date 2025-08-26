import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "../../data/dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "classifier.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")

def train():
    print("📥 Загружаем данные...")
    df = pd.read_csv(DATA_PATH)
    df.dropna(inplace=True)

    X = df["text"]
    y = df["label"]

    print(f"📊 Загружено {len(df)} записей")

    # Разделение на train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Создаём и обучаем векторизатор
    print("🔍 Обучаем TfidfVectorizer...")
    vectorizer = TfidfVectorizer(max_features=5000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Обучаем модель
    print("🤖 Обучаем модель LogisticRegression...")
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_vec, y_train)

    # Метрики
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    print(f"✅ Accuracy: {acc:.4f}, F1: {f1:.4f}")

    # Сохраняем модель и векторизатор
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    print(f"💾 Модель сохранена в {MODEL_PATH}")
    print(f"💾 Векторизатор сохранен в {VECTORIZER_PATH}")

if __name__ == "__main__":
    train()
