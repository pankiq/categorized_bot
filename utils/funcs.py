import asyncio
from aiogram import types
from config import bot, OWNER_ID

async def log_to_owner(text):
    """Пишет лог в консоль и отправляет его владельцу в ЛС"""
    print(f"LOG: {text}")
    try:
        await bot.send_message(OWNER_ID, f"🤖 SYSTEM LOG:\n{text}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить лог в ЛС: {e}")

async def delete_later(message: types.Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

def get_rank_info(points):
    """Функция расчета ранга"""
    tiers = [
        (50, "Страж"), (150, "Удаль"), (350, "Отвага"),
        (700, "Героизм"), (1500, "Величие"), (3500, "Легенда"),
        (float('inf'), "PVPGOD Барахолки")
    ]
    for threshold, title in tiers:
        if points < threshold:
            if threshold == float('inf'): return "PVPGOD Барахолки", 0
            needed = int(threshold - points)
            return title, needed     
    return "PVPGOD Барахолки", 0
