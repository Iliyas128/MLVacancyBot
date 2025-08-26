from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.db.database import (
    save_job_notification, 
    update_notification_status, 
    get_job_by_hash,
    mark_sent,
    already_sent,
    notification_already_sent
)
from src.bot.handlers import send_resume_via_telethon
from src.utils.email_sender import send_resume_email
import asyncio
from telethon.errors import FloodWaitError
from datetime import datetime

# Глобальная переменная для хранения Telethon клиента
telethon_client = None

def set_telethon_client(client):
    """Устанавливает Telethon клиент для отправки резюме"""
    global telethon_client
    telethon_client = client

async def send_job_notification(bot: Bot, job_hash: str, target_user: str = "iliyasls"):
    """
    Отправляет уведомление о новой вакансии с кнопками для отклика
    """
    # Получаем информацию о вакансии
    job_info = get_job_by_hash(job_hash)
    if not job_info:
        print(f"❌ Вакансия с хэшем {job_hash} не найдена")
        return None
    
    text, usernames, emails, links, prob, created_at = job_info
    
    # Проверяем, не отправляли ли уже уведомление для этой вакансии
    if notification_already_sent(job_hash, target_user):
        print(f"📨 Уведомление для вакансии {job_hash} уже отправлено пользователю {target_user}")
        return "already_sent"
    
    # Автоматически отправляем резюме по всем доступным контактам
    sent_count = 0
    errors = []
    
    print(f"🚀 Автоматически отправляем резюме для вакансии {job_hash}...")
    
    # Отправляем в Telegram
    if usernames and telethon_client:
        for username in usernames.split(","):
            username = username.strip()
            if username and not already_sent(username, job_hash):
                try:
                    success, error = await send_resume_via_telethon(
                        telethon_client, 
                        username, 
                        "data/resume.pdf"
                    )
                    if success:
                        mark_sent(username, job_hash)
                        sent_count += 1
                        print(f"✅ Резюме отправлено в Telegram -> {username}")
                    else:
                        errors.append(f"Telegram {username}: {error}")
                        print(f"❌ Ошибка отправки в Telegram {username}: {error}")
                except Exception as e:
                    errors.append(f"Telegram {username}: {str(e)}")
                    print(f"❌ Исключение при отправке в Telegram {username}: {e}")
    
    # Отправляем на email
    if emails:
        for email in emails.split(","):
            email = email.strip()
            if email and not already_sent(email, job_hash):
                try:
                    send_resume_email(email, "data/resume.pdf")
                    mark_sent(email, job_hash)
                    sent_count += 1
                    print(f"✅ Резюме отправлено по email -> {email}")
                except Exception as e:
                    errors.append(f"Email {email}: {str(e)}")
                    print(f"❌ Ошибка отправки email {email}: {e}")
    
    # Форматируем время в читаемом виде
    try:
        # Парсим время из БД и форматируем
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%d.%m.%Y %H:%M")
    except:
        formatted_time = created_at
    
    # Формируем текст уведомления
    notification_text = f"🎯 <b>Новая вакансия найдена!</b>\n\n"
    notification_text += f"📝 <b>Описание:</b>\n{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
    notification_text += f"📊 <b>Вероятность:</b> {prob:.2f}\n"
    
    # Добавляем контакты
    contacts = []
    if usernames:
        contacts.extend([f"@{u}" for u in usernames.split(",") if u.strip()])
    if emails:
        contacts.extend(emails.split(","))
    if links:
        contacts.extend(links.split(","))
    
    if contacts:
        notification_text += f"📞 <b>Контакты:</b> {', '.join(contacts[:3])}\n"
    
    # Добавляем информацию об автоматической отправке
    if sent_count > 0:
        notification_text += f"\n✅ <b>Резюме автоматически отправлено!</b>\n📤 Отправлено: {sent_count} контактов"
        if errors:
            notification_text += f"\n⚠️ Ошибки: {len(errors)}"
    else:
        notification_text += f"\n❌ <b>Не удалось отправить резюме</b>\n"
        if errors:
            notification_text += f"⚠️ Ошибки: {len(errors)}"
        else:
            notification_text += f"📝 Нет доступных контактов для отправки"
    
    # Создаем inline кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data=f"confirm_{job_hash}"),
            InlineKeyboardButton(text="❌ Пропустить", callback_data=f"skip_{job_hash}")
        ],
        [
            InlineKeyboardButton(text="📋 Полный текст", callback_data=f"full_{job_hash}")
        ]
    ])
    
    # Список возможных chat_id для отправки уведомлений
    # Добавьте сюда свой chat_id после первого запуска бота
    target_chat_ids = ["1011374221"
        # "YOUR_CHAT_ID_HERE",  # Замените на ваш chat_id
        # Можно добавить несколько chat_id для отправки нескольким пользователям
    ]
    
    # Отправляем уведомления по всем настроенным chat_id
    sent_count_notifications = 0
    for chat_id in target_chat_ids:
        try:
            message = await bot.send_message(
                chat_id=chat_id,
                text=notification_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            # Сохраняем информацию об уведомлении
            save_job_notification(job_hash, str(message.message_id), f"chat_{chat_id}")
            
            print(f"📨 Уведомление о вакансии отправлено в чат {chat_id}")
            sent_count_notifications += 1
            
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления в чат {chat_id}: {e}")
    
    return sent_count_notifications if sent_count_notifications > 0 else None

async def handle_notification_callback(callback: types.CallbackQuery, bot: Bot):
    """
    Обрабатывает нажатия на кнопки уведомлений
    """
    data = callback.data
    job_hash = data.split("_", 1)[1]
    
    try:
        if data.startswith("confirm_"):
            # Пользователь подтверждает отправку резюме
            await handle_confirm_job(callback, bot, job_hash)
            
        elif data.startswith("skip_"):
            # Пользователь пропустил вакансию
            await handle_skip_job(callback, bot, job_hash)
            
        elif data.startswith("full_"):
            # Показать полный текст вакансии
            await handle_show_full_text(callback, bot, job_hash)
            
    except Exception as e:
        print(f"❌ Ошибка обработки callback: {e}")
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

async def handle_confirm_job(callback: types.CallbackQuery, bot: Bot, job_hash: str):
    """
    Обрабатывает подтверждение отправки резюме
    """
    job_info = get_job_by_hash(job_hash)
    if not job_info:
        await callback.answer("Вакансия не найдена", show_alert=True)
        return
    
    text, usernames, emails, links, prob, created_at = job_info
    
    # Обновляем статус уведомления
    update_notification_status(str(callback.message.message_id), "confirmed")
    
    # Обновляем сообщение
    new_text = callback.message.text + "\n\n✅ <b>Отправка подтверждена!</b>"
    
    # Убираем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Полный текст", callback_data=f"full_{job_hash}")]
    ])
    
    await callback.message.edit_text(
        text=new_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer("Отправка подтверждена!")

async def handle_skip_job(callback: types.CallbackQuery, bot: Bot, job_hash: str):
    """
    Обрабатывает пропуск вакансии
    """
    # Обновляем статус уведомления
    update_notification_status(str(callback.message.message_id), "skipped")
    
    # Обновляем сообщение
    new_text = callback.message.text + "\n\n❌ <b>Вакансия пропущена</b>"
    
    # Убираем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Полный текст", callback_data=f"full_{job_hash}")]
    ])
    
    await callback.message.edit_text(
        text=new_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer("Вакансия пропущена")

async def handle_show_full_text(callback: types.CallbackQuery, bot: Bot, job_hash: str):
    """
    Показывает полный текст вакансии
    """
    job_info = get_job_by_hash(job_hash)
    if not job_info:
        await callback.answer("Вакансия не найдена", show_alert=True)
        return
    
    text, usernames, emails, links, prob, created_at = job_info
    
    # Отправляем полный текст в отдельном сообщении
    full_text = f"📋 <b>Полный текст вакансии:</b>\n\n{text}"
    
    if len(full_text) > 4096:
        # Разбиваем на части если текст слишком длинный
        parts = [full_text[i:i+4096] for i in range(0, len(full_text), 4096)]
        for i, part in enumerate(parts):
            await callback.message.answer(
                text=part,
                parse_mode="HTML"
            )
    else:
        await callback.message.answer(
            text=full_text,
            parse_mode="HTML"
        )
    
    await callback.answer("Полный текст отправлен")
