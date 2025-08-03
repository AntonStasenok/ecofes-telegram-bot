import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from bot.handlers.lead_handler import router
import logging
from bot.handlers.lead_handler import router

print("✅ Бот запущен: main.py стартовал", flush=True)
logging.basicConfig(level=logging.INFO)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
