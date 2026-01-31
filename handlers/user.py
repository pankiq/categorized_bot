from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_GUIDE, ADMIN_CHAT_ID
from database import get_user_data, get_rank_info
from utils.funcs import delete_later, log_to_owner

router = Router()

@router.message(Command("stats"))
async def stats_command(message: types.Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    data = get_user_data(target.id)
    
    wins, losses, points = data.get('wins', 0), data.get('losses', 0), data.get('points', 0)
    total = wins + losses
    winrate = round((wins / total) * 100, 1) if total > 0 else 0.0
    rank_title, points_needed = get_rank_info(points)
    
    # Определение класса и оружия (упрощенно)
    classes = {"🐍 Хантер": data.get('class_hunter', 0), "🔮 Варлок": data.get('class_warlock', 0), "🛡 Титан": data.get('class_titan', 0)}
    fav_class = max(classes, key=classes.get)
    if classes[fav_class] == 0: fav_class = "Не определен"
    
    weapons = {"♠️ Ace": data.get('w_ace', 0), "🤠 LW": data.get('w_lw', 0), "🔥 GG": data.get('w_gg', 0), "🟣 Nova": data.get('w_nova', 0), "⚡ Crash": data.get('w_crash', 0)}
    fav_weapon = max(weapons, key=weapons.get)
    if weapons[fav_weapon] == 0: fav_weapon = "Кулаки"

    text = (
        f"📊 <b>ДОСЬЕ ГОРНИЛА:</b> @{target.username}\n━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Ранг:</b> {rank_title} ({points} очков)\n"
        f"⚔️ <b>Матчей:</b> {total} (WR: {winrate}%)\n"
        f"✅ <b>W:</b> {wins} | ❌ <b>L:</b> {losses}\n"
        f"❤️ {fav_class} | 🔫 {fav_weapon}"
    )
    msg = await message.reply(text)
    asyncio.create_task(delete_later(msg, 60))

@router.message(Command("help"))
async def help_command(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔧 Гайд по боту", url=BOT_GUIDE)]])
    msg = await message.answer(
        "<b>✅ Команды:</b>\n/duel — Вызов на бой\n/stats — Статистика\n/report — Пожаловаться\n/lw — Рулетка",
        reply_markup=kb
    )
    asyncio.create_task(delete_later(msg, 15))

@router.message(Command("report"))
async def report_command(message: types.Message):
    if not message.reply_to_message:
        msg = await message.reply("⚠️ Используй команду в ответ на сообщение.")
        asyncio.create_task(delete_later(msg, 5)); return

    reported = message.reply_to_message
    chat_str = str(message.chat.id).replace("-100", "")
    link = f"https://t.me/c/{chat_str}/{reported.message_id}" if not message.chat.username else f"https://t.me/{message.chat.username}/{reported.message_id}"

    text = f"🚨 <b>РЕПОРТ</b>\n🕵️‍♂️ От: @{message.from_user.username}\n💀 На: @{reported.from_user.username}\n👉 {link}"
    try:
        from config import bot # Local import
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
        msg = await message.answer("✅ Отправлено Авангарду.")
        asyncio.create_task(delete_later(msg, 5))
    except Exception as e:
        await log_to_owner(f"❌ Ошибка репорта: {e}")
