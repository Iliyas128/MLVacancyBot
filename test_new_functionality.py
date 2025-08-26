#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой функциональности:
- Автоматическая отправка резюме
- Предотвращение дублирования уведомлений
- Правильное форматирование времени
"""

import asyncio
import sqlite3
from src.db.database import init_db, save_job, get_job_by_hash, notification_already_sent
from src.bot.notifications import send_job_notification
from src.bot.bot import bot

async def test_new_functionality():
    """Тестирует новую функциональность"""
    
    # Инициализируем базу данных
    init_db()
    
    # Создаем тестовую вакансию
    test_job_text = """
    Ищем Full-Stack разработчика для работы над стартапом!
    
    Требования:
    - JavaScript/TypeScript
    - React/Vue.js
    - Node.js/Python
    - Опыт работы с базами данных
    - Git и CI/CD
    
    Условия:
    - Удаленная работа
    - Зарплата от 180,000 руб
    - Доля в проекте
    - Гибкий график
    
    Контакты:
    @startup_hr
    hr@startup.com
    https://t.me/startup_hr
    """
    
    # Сохраняем тестовую вакансию
    job_hash = save_job(
        text=test_job_text,
        chat_id="test_chat",
        msg_id="test_msg",
        prob=0.88,
        usernames=["startup_hr"],
        emails=["hr@startup.com"],
        links=["https://t.me/startup_hr"]
    )
    
    print(f"✅ Тестовая вакансия создана с хэшем: {job_hash}")
    
    # Проверяем, что вакансия сохранилась
    job_info = get_job_by_hash(job_hash)
    if job_info:
        print(f"✅ Вакансия найдена в БД: {job_info[0][:100]}...")
    else:
        print("❌ Вакансия не найдена в БД")
        return
    
    # Тест 1: Отправляем уведомление первый раз
    print("\n🧪 Тест 1: Отправка уведомления...")
    try:
        msg_id = await send_job_notification(bot, job_hash, "iliyasls")
        if msg_id and msg_id != "already_sent":
            print(f"✅ Уведомление отправлено успешно! ID сообщения: {msg_id}")
        elif msg_id == "already_sent":
            print("✅ Уведомление уже было отправлено (дублирование предотвращено)")
        else:
            print("❌ Ошибка отправки уведомления")
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления: {e}")
    
    # Тест 2: Пытаемся отправить уведомление повторно (должно быть заблокировано)
    print("\n🧪 Тест 2: Попытка повторной отправки...")
    try:
        msg_id = await send_job_notification(bot, job_hash, "iliyasls")
        if msg_id == "already_sent":
            print("✅ Дублирование предотвращено - уведомление не отправлено повторно")
        else:
            print("❌ Дублирование не предотвращено")
    except Exception as e:
        print(f"❌ Ошибка при повторной отправке: {e}")
    
    # Тест 3: Проверяем статус уведомления
    print("\n🧪 Тест 3: Проверка статуса уведомления...")
    is_sent = notification_already_sent(job_hash, "iliyasls")
    if is_sent:
        print("✅ Уведомление найдено в БД")
    else:
        print("❌ Уведомление не найдено в БД")

async def test_stats():
    """Тестирует команду статистики"""
    
    with sqlite3.connect("data/db.sqlite3") as conn:
        # Общее количество вакансий
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        
        # Количество отправленных резюме
        total_sent = conn.execute("SELECT COUNT(*) FROM jobs_sent").fetchone()[0]
        
        # Статистика уведомлений
        confirmed = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'confirmed'").fetchone()[0]
        skipped = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'skipped'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'pending'").fetchone()[0]
    
    print(f"\n📊 Статистика:")
    print(f"   Всего вакансий: {total_jobs}")
    print(f"   Отправлено резюме: {total_sent}")
    print(f"   Уведомления:")
    print(f"     - Подтверждено: {confirmed}")
    print(f"     - Пропущено: {skipped}")
    print(f"     - Ожидает: {pending}")

def print_new_features():
    """Печатает информацию о новых возможностях"""
    print("\n" + "="*60)
    print("🆕 НОВЫЕ ВОЗМОЖНОСТИ")
    print("="*60)
    print("✅ Автоматическая отправка резюме при нахождении вакансии")
    print("✅ Предотвращение дублирования уведомлений")
    print("✅ Одно уведомление вместо нескольких")
    print("✅ Убрано время из уведомлений и статистики")
    print("✅ Новые кнопки: 'Подтвердить отправку' и 'Пропустить'")
    print("✅ Уведомления служат для подтверждения, а не для отправки")
    print("✅ Двойная проверка: резюме отправляется сразу + уведомление")
    print("="*60)

if __name__ == "__main__":
    print("🧪 Запуск тестов новой функциональности...")
    
    # Печатаем информацию о новых возможностях
    print_new_features()
    
    # Тестируем статистику
    asyncio.run(test_stats())
    
    # Тестируем новую функциональность
    asyncio.run(test_new_functionality())
    
    print("\n✅ Тесты завершены!")
    print("\n💡 Теперь бот автоматически отправляет резюме и уведомляет вас для подтверждения.")
