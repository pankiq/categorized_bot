import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Импортируем настройки и переменные
from config import BOT_TOKEN
from state import ACTIVE_DUELS
from database import load_duels

# Импортируем роутеры (твои новые файлы)
from handlers import moderation, games, ai, user, admin
from utils.funcs import send_morning_voice, log_to_owner

# Логирование
logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # ПОДКЛЮЧАЕМ ВСЕ ЧАСТИ (ПОРЯДОК ВАЖЕН)
    # Сначала фильтры и рулетка
    dp.include_router(moderation.router)
    # Потом игры и дуэли
    dp.include_router(games.router)
    # Потом админка
    dp.include_router(admin.router)
    # Потом ИИ
    dp.include_router(ai.router)
    # В конце общие команды
    dp.include_router(user.router)

    # Загружаем недоигранные дуэли из файла
    try:
        loaded = load_duels()
        ACTIVE_DUELS.update(loaded)
        print(f"✅ Загружено дуэлей из кэша: {len(loaded)}")
    except:
        print("ℹ️ Кэш дуэлей пуст")

    # Настройка планировщика (утренний войс)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_morning_voice, "cron", hour=7, minute=0, args=[bot])
    scheduler.start()

    print(f"🚀 Бот запущен! Время: {datetime.now()}")
    await log_to_owner(bot, "🤖 Бот успешно перезагружен и готов к бою!")

    # Чистим старые сообщения и запускаем
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⭕ Бот остановлен")
