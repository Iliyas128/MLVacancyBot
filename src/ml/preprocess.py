import re
import string
from nltk.corpus import stopwords

stop_words = set(stopwords.words('russian') +  stopwords.words('english'))

def clean_text(text:str) -> str:
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)  # ссылки
    text = re.sub(r'@\w+', '', text)  # упоминания
    text = re.sub(r'#\w+', '', text)  # хэштеги
    text = re.sub(r'\d+', '', text)  # числа
    text = text.translate(str.maketrans('', '', string.punctuation))  # пунктуация
    tokens = [word for word in text.split() if word not in stop_words]
    return ' '.join(tokens)