import os
import re
import asyncio
from telethon.errors.rpcerrorlist import (
    UserPrivacyRestrictedError,
    UserIsBlockedError,
    ChatWriteForbiddenError,
    PeerIdInvalidError,
    FloodWaitError,
)

MAX_MESSAGE_LENGTH = 4000

def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH):
    """Разбивает длинный текст на части для Telegram (для ответов бота пользователю)."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def extract_emails(text: str):
    return re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)

def extract_telegram_usernames(text: str):
    """
    Достаём @usernames, избегая email.
    Матчится только если перед @ пробел/начало строки.
    """
    text_wo_emails = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', ' ', text)
    usernames = re.findall(r'(?<!\S)@([A-Za-z0-9_]{5,32})\b', text_wo_emails)

    # Уникализируем, сохраняем порядок
    seen, out = set(), []
    for u in usernames:
        if u.lower() not in seen:
            seen.add(u.lower())
            out.append(u)
    return out

def extract_links(text: str):
    """Достаём http/https ссылки."""
    links = re.findall(r'(https?://[^\s\)\]\}]+)', text)
    seen, out = set(), []
    for l in links:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out

def extract_usernames_from_links(links: list[str]):
    """
    Достаём username только из Telegram-ссылок вида:
    - https://t.me/username
    - http://t.me/username
    """
    usernames = []
    for link in links:
        match = re.search(r'(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})', link)
        if match:
            uname = match.group(1)
            if uname not in usernames:
                usernames.append(uname)
    return usernames

async def send_resume_via_telethon(client, employer_username: str, resume_path: str = "data/resume.pdf",
                                   greeting: str = "Здравствуйте! Вот моё резюме."):
    """
    Отправляет приветственное сообщение и PDF резюме через Telethon.
    Возвращает (success: bool, error: str|None)
    """
    uname = (employer_username or "").strip()
    if not uname:
        return False, "empty_username"

    if not uname.startswith("@"):
        uname = "@" + uname

    try:
        entity = await client.get_entity(uname)
        await client.send_message(entity, greeting)

        if os.path.exists(resume_path):
            await client.send_file(entity, resume_path, caption="Резюме (PDF)")
        else:
            await client.send_message(entity, "PDF резюме временно недоступно — ответьте, и я дошлю ссылку.")

        print(f"✅ Резюме отправлено {uname}")
        return True, None

    except FloodWaitError as e:
        print(f"⏳ FloodWaitError: нужно подождать {e.seconds} сек для {uname}")
        return False, f"floodwait_{e.seconds}s"
    except (UserPrivacyRestrictedError, UserIsBlockedError, ChatWriteForbiddenError, PeerIdInvalidError) as e:
        print(f"⚠️ Нельзя написать пользователю {uname}: {e.__class__.__name__}")
        return False, e.__class__.__name__
    except Exception as e:
        print(f"❌ Ошибка при отправке резюме {uname}: {e}")
        return False, str(e)
