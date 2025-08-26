import sqlite3
import hashlib

DB_PATH = "data/db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Старая таблица для совместимости с /jobs (если ты её уже используешь)
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT
        )""")
        # Новая таблица вакансий
        conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            chat_id TEXT,
            msg_id TEXT,
            prob REAL,
            usernames TEXT,
            emails TEXT,
            links TEXT,
            hash TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        # Кому уже отправляли резюме по конкретной вакансии
        conn.execute("""CREATE TABLE IF NOT EXISTS jobs_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text_hash TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        # Таблица для отслеживания уведомлений о вакансиях
        conn.execute("""CREATE TABLE IF NOT EXISTS job_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_hash TEXT,
            notification_msg_id TEXT,
            sent_to_user TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_hash) REFERENCES jobs (hash)
        )""")
    
    # Очищаем дублирующие записи при инициализации
    cleanup_duplicate_usernames()
    # Очищаем старые записи
    cleanup_old_records()

def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]

def save_message(text: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO messages (text) VALUES (?)", (text,))

def get_all_messages():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT text FROM messages ORDER BY id DESC")
        return [r[0] for r in cur.fetchall()]

def save_job(text, chat_id=None, msg_id=None, prob=None, usernames=None, emails=None, links=None):
    h = _hash_text(text)
    usernames_s = ",".join(usernames or [])
    emails_s = ",".join(emails or [])
    links_s = ",".join(links or [])
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""INSERT OR IGNORE INTO jobs
                        (text, chat_id, msg_id, prob, usernames, emails, links, hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (text, str(chat_id) if chat_id is not None else None,
                      str(msg_id) if msg_id is not None else None,
                      prob, usernames_s, emails_s, links_s, h))
    return h  # возвращаем хэш для связи

def _normalize_username(username: str) -> str:
    """Нормализует username: убирает @ и приводит к нижнему регистру"""
    username = username.strip()
    if username.startswith("@"):
        username = username[1:]
    return username.lower()

def already_sent(username: str, text_hash: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        normalized_username = _normalize_username(username)
        # Проверяем, отправляли ли мы резюме этому пользователю за последние 24 часа
        cur = conn.execute("""
            SELECT sent_at FROM jobs_sent 
            WHERE username=? AND sent_at > datetime('now', '-1 day') 
            ORDER BY sent_at DESC LIMIT 1
        """, (normalized_username,))
        result = cur.fetchone()
        if result:
            print(f"   ⏰ Последняя отправка {normalized_username}: {result[0]}")
        return result is not None

def mark_sent(username: str, text_hash: str):
    with sqlite3.connect(DB_PATH) as conn:
        normalized_username = _normalize_username(username)
        # Сохраняем запись с текущим временем
        conn.execute("INSERT INTO jobs_sent (username, text_hash, sent_at) VALUES (?, ?, datetime('now'))",
                     (normalized_username, text_hash))

def get_recent_jobs(limit: int = 10):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""SELECT text, usernames, emails, links, prob, created_at
                              FROM jobs ORDER BY id DESC LIMIT ?""", (limit,))
        return cur.fetchall()

def get_jobs_sent():
    """Отладочная функция для просмотра таблицы jobs_sent"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT username, text_hash, sent_at FROM jobs_sent ORDER BY sent_at DESC")
        return cur.fetchall()

def cleanup_duplicate_usernames():
    """Очищает дублирующие записи в jobs_sent, оставляя только нормализованные username"""
    with sqlite3.connect(DB_PATH) as conn:
        # Получаем все записи
        cur = conn.execute("SELECT username, text_hash, sent_at FROM jobs_sent")
        records = cur.fetchall()
        
        # Группируем по нормализованному username и text_hash
        normalized_records = {}
        for username, text_hash, sent_at in records:
            normalized_username = _normalize_username(username)
            key = (normalized_username, text_hash)
            if key not in normalized_records:
                normalized_records[key] = (normalized_username, text_hash, sent_at)
        
        # Очищаем таблицу и вставляем только уникальные записи
        conn.execute("DELETE FROM jobs_sent")
        for normalized_username, text_hash, sent_at in normalized_records.values():
            conn.execute("INSERT INTO jobs_sent (username, text_hash, sent_at) VALUES (?, ?, ?)",
                        (normalized_username, text_hash, sent_at))
        
        print(f"🧹 Очищено дублирующих записей. Осталось {len(normalized_records)} уникальных записей.")

def cleanup_old_records():
    """Удаляет записи старше 7 дней"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM jobs_sent WHERE sent_at < datetime('now', '-7 days')")
        deleted_count = cur.rowcount
        print(f"🗑️ Удалено {deleted_count} старых записей (старше 7 дней)")

def save_job_notification(job_hash: str, notification_msg_id: str, sent_to_user: str):
    """Сохраняет информацию об отправленном уведомлении о вакансии"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""INSERT INTO job_notifications 
                        (job_hash, notification_msg_id, sent_to_user, status)
                        VALUES (?, ?, ?, 'pending')""",
                     (job_hash, notification_msg_id, sent_to_user))

def update_notification_status(notification_msg_id: str, status: str):
    """Обновляет статус уведомления (applied/not_applied)"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""UPDATE job_notifications 
                        SET status = ? 
                        WHERE notification_msg_id = ?""",
                     (status, notification_msg_id))

def get_job_by_hash(job_hash: str):
    """Получает информацию о вакансии по хэшу"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""SELECT text, usernames, emails, links, prob, created_at
                              FROM jobs WHERE hash = ?""", (job_hash,))
        return cur.fetchone()

def get_pending_notifications_count():
    """Получает количество ожидающих уведомлений"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""SELECT COUNT(*) FROM job_notifications 
                              WHERE status = 'pending'""")
        return cur.fetchone()[0]

def notification_already_sent(job_hash: str, target_user: str) -> bool:
    """Проверяет, было ли уже отправлено уведомление для данной вакансии"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""SELECT COUNT(*) FROM job_notifications 
                              WHERE job_hash = ? AND sent_to_user = ?""", 
                          (job_hash, target_user))
        return cur.fetchone()[0] > 0

def get_job_notification_status(job_hash: str, target_user: str):
    """Получает статус уведомления для вакансии"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""SELECT status, created_at FROM job_notifications 
                              WHERE job_hash = ? AND sent_to_user = ?""", 
                          (job_hash, target_user))
        return cur.fetchone()
