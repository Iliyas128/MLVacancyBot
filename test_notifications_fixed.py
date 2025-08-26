#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы уведомлений о вакансиях с Chat ID
"""

import asyncio
import sqlite3
from src.db.database import init_db, save_job, get_job_by_hash
from src.bot.notifications import send_job_notification
from src.bot.bot import bot

async def test_notification_with_chat_id():
    """Тестирует отправку уведомления о вакансии с использованием Chat ID"""
    
    # Инициализируем базу данных
    init_db()
    
    # Создаем тестовую вакансию
    test_job_text = """
    Ищем Senior Python разработчика для работы над AI проектом!
    
    Требования:
    - Python 3.8+
    - Опыт работы с ML/AI библиотеками (TensorFlow, PyTorch)
    - Знание Django/Flask
    - Опыт работы с Docker
    - Знание SQL и NoSQL баз данных
    
    Условия:
    - Удаленная работа
    - Зарплата от 200,000 руб
    - Полная занятость
    - Гибкий график
    
    Контакты:
    @hr_ai_company
    hr@ai-company.com
    https://t.me/hr_ai_company
    """
    
    # Сохраняем тестовую вакансию
    job_hash = save_job(
        text=test_job_text,
        chat_id="test_chat",
        msg_id="test_msg",
        prob=0.92,
        usernames=["hr_ai_company"],
        emails=["hr@ai-company.com"],
        links=["https://t.me/hr_ai_company"]
    )
    
    print(f"✅ Тестовая вакансия создана с хэшем: {job_hash}")
    
    # Проверяем, что вакансия сохранилась
    job_info = get_job_by_hash(job_hash)
    if job_info:
        print(f"✅ Вакансия найдена в БД: {job_info[0][:100]}...")
    else:
        print("❌ Вакансия не найдена в БД")
        return
    
    # Отправляем уведомление
    print("📨 Отправляем тестовое уведомление...")
    try:
        msg_id = await send_job_notification(bot, job_hash, "iliyasls")
        if msg_id:
            print(f"✅ Уведомление отправлено успешно! ID сообщения: {msg_id}")
        else:
            print("❌ Ошибка отправки уведомления")
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления: {e}")

async def test_stats():
    """Тестирует команду статистики"""
    
    with sqlite3.connect("data/db.sqlite3") as conn:
        # Общее количество вакансий
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        
        # Количество отправленных резюме
        total_sent = conn.execute("SELECT COUNT(*) FROM jobs_sent").fetchone()[0]
        
        # Статистика уведомлений
        applied = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'applied'").fetchone()[0]
        not_applied = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'not_applied'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM job_notifications WHERE status = 'pending'").fetchone()[0]
    
    print(f"📊 Статистика:")
    print(f"   Всего вакансий: {total_jobs}")
    print(f"   Отправлено резюме: {total_sent}")
    print(f"   Уведомления:")
    print(f"     - Откликнулся: {applied}")
    print(f"     - Пропустил: {not_applied}")
    print(f"     - Ожидает: {pending}")

def print_setup_instructions():
    """Печатает инструкции по настройке"""
    print("\n" + "="*60)
    print("🔧 ИНСТРУКЦИИ ПО НАСТРОЙКЕ УВЕДОМЛЕНИЙ")
    print("="*60)
    print("1. Запустите бота: python main.py")
    print("2. Отправьте боту команду: /myid")
    print("3. Скопируйте ваш Chat ID из ответа")
    print("4. Откройте файл: src/bot/notifications.py")
    print("5. Найдите строку: target_chat_ids = []")
    print("6. Добавьте ваш Chat ID:")
    print("   target_chat_ids = [")
    print("       'ВАШ_CHAT_ID_ЗДЕСЬ',")
    print("   ]")
    print("7. Перезапустите бота")
    print("8. Запустите этот тест: python test_notifications_fixed.py")
    print("="*60)

if __name__ == "__main__":
    print("🧪 Запуск тестов уведомлений с Chat ID...")
    
    # Печатаем инструкции
    print_setup_instructions()
    
    # Тестируем статистику
    asyncio.run(test_stats())
    
    # Тестируем отправку уведомления
    asyncio.run(test_notification_with_chat_id())
    
    print("✅ Тесты завершены!")
    print("\n💡 Если уведомления не приходят, следуйте инструкциям выше для настройки Chat ID.")
