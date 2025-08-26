import asyncio
from src.bot.bot import start_bot, bot
from src.parser.telethone_client import start_parser, set_bot_instance, client
from src.bot.notifications import set_telethon_client
from src.db.database import init_db

async def main():
    init_db()  # создаём таблицы, если их нет
    
    # Передаем экземпляр бота в парсер для отправки уведомлений
    set_bot_instance(bot)
    
    # Передаем Telethon клиент в модуль уведомлений
    set_telethon_client(client)
    
    await asyncio.gather(
        start_parser(),  # Telethon userbot (чтение чатов + автоотправка резюме)
        start_bot()      # Aiogram bot (команды /jobs и т.п.)
    )

if __name__ == "__main__":
    asyncio.run(main())
