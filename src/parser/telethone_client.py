from telethon import TelegramClient, events
from config.config import API_ID, API_HASH
from src.db.database import save_job, mark_sent, already_sent, get_jobs_sent
from src.ml.classifier import predict
from src.bot.handlers import send_resume_via_telethon
from src.utils.email_sender import send_resume_email
from src.bot.notifications import send_job_notification
import re
import requests
from bs4 import BeautifulSoup
import asyncio
from telethon.errors import FloodWaitError

client = TelegramClient('userbot_session', API_ID, API_HASH)
THRESHOLD = 0.60  # минимальный порог вероятности
RESUME_PATH = "data/resume.pdf"
BLOCKED_USERNAMES = {"@teletype", "@telegram","@gmail", "@quinton_nietfeld", "@kovesh"}
BLOCKED_EMAIL_DOMAINS = ["teletype.in", "telegram.org", "noreply"]

# Глобальная переменная для хранения экземпляра бота
bot_instance = None

def set_bot_instance(bot):
    """Устанавливает экземпляр бота для отправки уведомлений"""
    global bot_instance
    bot_instance = bot

# --- Функция для извлечения контактов ---
def extract_contacts_from_text(text):
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    usernames = []
    links = re.findall(r"https?://\S+", text)

    # --- Проверяем HTML (если есть) ---
    soup = BeautifulSoup(text, "html.parser")

    # Ищем <a href="...t.me/...">@username</a>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "t.me/" in href or "telegram.me/" in href:
            uname = re.search(r"t\.me/([a-zA-Z0-9_]{3,32})", href)
            if uname:
                usernames.append("@" + uname.group(1))

    # --- Извлекаем username из обычного текста ---
    usernames += re.findall(r"@([a-zA-Z0-9_]{3,32})", text)
    usernames = ["@" + u if not u.startswith("@") else u for u in usernames]

    # --- Обрабатываем ссылки (ищем контакты на странице) ---
    for link in links:
        try:
            response = requests.get(link, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code == 200:
                html = response.text
                page_soup = BeautifulSoup(html, "html.parser")

                # 1. Извлекаем весь текст страницы
                page_text = page_soup.get_text(separator=" ", strip=True)

                # 2. Ищем email
                emails += re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_text)

                # 3. Ищем usernames
                page_usernames = re.findall(r"@([a-zA-Z0-9_]{3,32})", page_text)
                usernames += ["@" + u for u in page_usernames]

                # 4. Ищем в <a href>
                for a in page_soup.find_all("a", href=True):
                    href = a["href"]
                    if "t.me/" in href or "telegram.me/" in href:
                        uname = re.search(r"t\.me/([a-zA-Z0-9_]{3,32})", href)
                        if uname:
                            usernames.append("@" + uname.group(1))

        except Exception as e:
            print(f"⚠ Ошибка при обработке ссылки {link}: {e}")

    return list(set(emails)), list(set(usernames)), links

# --- Фильтрация запрещённых контактов ---
def filter_contacts(emails, usernames):
    """Фильтруем email и username: убираем заблокированные и дубли."""
    # Фильтруем email по доменам
    filtered_emails = []
    seen_emails = set()
    for email in emails:
        domain = email.split('@')[-1].lower()
        if domain not in BLOCKED_EMAIL_DOMAINS and email not in seen_emails:
            filtered_emails.append(email)
            seen_emails.add(email)

    # Фильтруем usernames по чёрному списку
    filtered_usernames = []
    seen_users = set()
    for uname in usernames:
        original_uname = uname
        uname = uname.strip()
        if not uname.startswith("@"):
            uname = "@" + uname
        
        print(f"🔍 Проверяем username: '{original_uname}' -> '{uname}'")
        print(f"   В BLOCKED_USERNAMES: {uname in BLOCKED_USERNAMES}")
        print(f"   Уже видели: {uname.lower() in seen_users}")
        
        if uname not in BLOCKED_USERNAMES and uname.lower() not in seen_users:
            filtered_usernames.append(uname)
            seen_users.add(uname.lower())
            print(f"   ✅ Добавлен в filtered_usernames")
        else:
            print(f"   ❌ Отфильтрован")

    return filtered_emails, filtered_usernames

async def start_parser():
    await client.start()
    print("✅ Telethon parser запущен...")

    @client.on(events.NewMessage)
    async def handler(event):
        text = event.message.message or ""
        if not text.strip():
            return

        # --- Классификация текста ---
        label, prob = predict(text)

        # --- Извлекаем контакты ---
        emails, usernames, links = extract_contacts_from_text(text)
        
        print("🔍 ДО фильтрации:")
        print("Emails:", emails)
        print("Usernames:", usernames)
        print("Links:", links)

        # --- Фильтруем запрещённые ---
        emails, usernames = filter_contacts(emails, usernames)
        
        print("🔍 ПОСЛЕ фильтрации:")
        print("Emails:", emails)
        print("Usernames:", usernames)
        print("Links:", links)

        job_hash = save_job(
            text=text,
            chat_id=event.chat_id,
            msg_id=event.message.id,
            prob=prob,
            usernames=usernames,
            links=links,
            emails=emails
        )

        print(f"\n📌 Новое сообщение:")
        print(f"Текст: {text[:120]}...")
        print(f"Вероятность вакансии: {prob:.4f}, Метка: {label}")
        print(f"Usernames: {usernames}, Links: {links}, Emails: {emails}")

        if label == 1 and prob >= THRESHOLD:
            # Отправляем уведомление о вакансии
            if bot_instance:
                try:
                    await send_job_notification(bot_instance, job_hash, "iliyasls")
                    print(f"📨 Уведомление о вакансии отправлено")
                except Exception as e:
                    print(f"❌ Ошибка отправки уведомления: {e}")
            
            # Резюме теперь отправляется автоматически в функции уведомлений
            print("ℹ Резюме будет отправлено автоматически через уведомления")
        else:
            print("❌ Не подходит или нет контактов.")

    await client.run_until_disconnected()

