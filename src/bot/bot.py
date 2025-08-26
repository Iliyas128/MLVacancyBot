from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config.config import BOT_TOKEN
from src.db.database import get_recent_jobs, get_pending_notifications_count
from src.bot.handlers import split_message
from src.bot.notifications import handle_notification_callback
import sqlite3
from datetime import datetime

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я ищу вакансии и автоматически отправляю резюме по найденным контактам.\n\n📋 <b>Команды:</b>\n• /jobs - последние найденные вакансии\n• /notifications - ожидающие уведомления\n• /stats - статистика откликов\n• /cleanup - очистка старых данных\n• /myid - получить ваш Chat ID для настройки уведомлений\n\n📨 <b>Уведомления:</b>\nПри нахождении новой вакансии вы получите уведомление с кнопками для отклика.", parse_mode="HTML")

@dp.message(Command("jobs"))
async def jobs(message: types.Message):
    rows = get_recent_jobs(limit=10)
    if not rows:
        await message.answer("Пока вакансий нет.")
        return

    # компактный список превью
    lines = []
    for text, usernames, emails, links, prob, created_at in rows:
        preview = (text.replace("\n", " ").strip()[:200] + ("…" if len(text) > 200 else ""))
        parts = []
        if usernames:
            parts.append("@" + usernames.split(",")[0])
        if emails:
            parts.append(emails.split(",")[0])
        if links:
            parts.append(links.split(",")[0])
        contact = " | ".join(parts) if parts else "контактов нет"
        lines.append(f"• {preview}\n  score: {prob:.2f} | {contact}")

    full = "Последние вакансии:\n\n" + "\n\n".join(lines)
    for chunk in split_message(full):
        await message.answer(chunk)

@dp.message(Command("notifications"))
async def notifications(message: types.Message):
    count = get_pending_notifications_count()
    if count == 0:
        await message.answer("Нет ожидающих уведомлений о вакансиях.")
    else:
        await message.answer(f"У вас есть {count} ожидающих уведомлений о вакансиях.")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    """Показывает статистику откликов"""
    import sqlite3
    
    with sqlite3.connect("data/db.sqlite3") as conn:
        # Общее количество вакансий
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        
        # Количество отправленных резюме
        total_sent = conn.execute("SELECT COUNT(*) FROM jobs_sent").fetchone()[0]
        
        # Статистика уведомлений
        confirmed = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'confirmed'").fetchone()[0]
        skipped = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'skipped'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'pending'").fetchone()[0]
        
        # Последние 5 откликов
        recent_sent = conn.execute("""
            SELECT username, sent_at FROM jobs_sent 
            ORDER BY sent_at DESC LIMIT 5
        """).fetchall()
    
    stats_text = f"📊 <b>Статистика откликов:</b>\n\n"
    stats_text += f"📋 Всего вакансий найдено: {total_jobs}\n"
    stats_text += f"📤 Всего резюме отправлено: {total_sent}\n\n"
    stats_text += f"🎯 <b>Уведомления:</b>\n"
    stats_text += f"✅ Подтверждено: {confirmed}\n"
    stats_text += f"❌ Пропущено: {skipped}\n"
    stats_text += f"⏳ Ожидает: {pending}\n\n"
    
    if recent_sent:
        stats_text += f"📅 <b>Последние отклики:</b>\n"
        for username, sent_at in recent_sent:
            stats_text += f"• @{username}\n"
    
    await message.answer(stats_text, parse_mode="HTML")

@dp.message(Command("cleanup"))
async def cleanup(message: types.Message):
    """Очищает старые уведомления и записи"""
    import sqlite3
    
    with sqlite3.connect("data/db.sqlite3") as conn:
        # Удаляем уведомления старше 30 дней
        old_notifications = conn.execute("""
            DELETE FROM job_notifications 
            WHERE created_at < datetime('now', '-30 days')
        """).rowcount
        
        # Удаляем записи об отправке старше 30 дней
        old_sent = conn.execute("""
            DELETE FROM jobs_sent 
            WHERE sent_at < datetime('now', '-30 days')
        """).rowcount
        
        # Удаляем вакансии старше 60 дней
        old_jobs = conn.execute("""
            DELETE FROM jobs 
            WHERE created_at < datetime('now', '-60 days')
        """).rowcount
    
    cleanup_text = f"🧹 <b>Очистка завершена:</b>\n\n"
    cleanup_text += f"🗑️ Удалено уведомлений: {old_notifications}\n"
    cleanup_text += f"🗑️ Удалено записей об отправке: {old_sent}\n"
    cleanup_text += f"🗑️ Удалено вакансий: {old_jobs}\n"
    
    await message.answer(cleanup_text, parse_mode="HTML")

@dp.message(Command("myid"))
async def myid(message: types.Message):
    """Показывает chat_id пользователя для настройки уведомлений"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or "Нет username"
    
    info_text = f"📋 <b>Ваша информация:</b>\n\n"
    info_text += f"🆔 <b>User ID:</b> {user_id}\n"
    info_text += f"💬 <b>Chat ID:</b> {chat_id}\n"
    info_text += f"👤 <b>Username:</b> @{username}\n\n"
    info_text += f"💡 <b>Для настройки уведомлений:</b>\n"
    info_text += f"Добавьте ваш Chat ID ({chat_id}) в список target_chat_ids в файле src/bot/notifications.py"
    
    await message.answer(info_text, parse_mode="HTML")

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    """Обрабатывает все callback'и от inline кнопок"""
    await handle_notification_callback(callback, bot)

async def start_bot():
    print("✅ Aiogram бот запущен...")
    await dp.start_polling(bot)
