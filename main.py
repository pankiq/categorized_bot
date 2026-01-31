import asyncio
import logging
import pytz
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import bot, CHAT_ID
from state import USED_LORE_FACTS, LAST_MESSAGE_TIME
from utils.texts import LORE_FACTS
from utils.funcs import send_morning_voice, log_to_owner
from middlewares import AntiFloodMiddleware

# Импорт роутеров
from aiogram import Dispatcher
from handlers import admin, user, games, ai, moderation

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# Подключаем роутеры (важен порядок!)
dp.include_router(admin.router)
dp.include_router(user.router)
dp.include_router(games.router)
dp.include_router(ai.router)
dp.include_router(moderation.router) # Модерация в конце, т.к. ловит все сообщения

dp.message.middleware(AntiFloodMiddleware())

async def check_silence_loop():
    """Фоновая задача для отправки фактов, если в чате тихо"""
    global USED_LORE_FACTS, LAST_MESSAGE_TIME
    while True:
        await asyncio.sleep(300)
        if (datetime.now() - LAST_MESSAGE_TIME).total_seconds() > 3600:
            if len(USED_LORE_FACTS) >= len(LORE_FACTS): USED_LORE_FACTS = []
            
            avail = [i for i in range(len(LORE_FACTS)) if i not in USED_LORE_FACTS]
            if avail:
                idx = random.choice(avail)
                USED_LORE_FACTS.append(idx)
                try:
                    await bot.send_message(CHAT_ID, f"📢 <b>Минутка Лора:</b>\n{LORE_FACTS[idx]}")
                    LAST_MESSAGE_TIME = datetime.now()
                except Exception as e:
                    print(f"Lore error: {e}")

async def main():
    print("Бот запускается...")
    
    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_morning_voice, "cron", hour=7, minute=0, timezone=pytz.timezone("Europe/Moscow"))
    scheduler.start()
    
    # Фоновые задачи
    asyncio.create_task(check_silence_loop())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
