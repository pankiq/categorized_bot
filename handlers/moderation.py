import random
import re
import asyncio
from datetime import timedelta, datetime
from aiogram import Router, types, F
from aiogram.types import ChatPermissions, ReactionTypeEmoji, InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, OWNER_ID, LINK_RULES, LINK_CHAT, LINK_TAPIR_GUIDE, KEEP_POSTED_STICKER_ID
from state import PENDING_VERIFICATION, SILENT_MODE_USERS, CHAT_HISTORY, PROCESSED_ALBUMS, LAST_MESSAGE_TIME
from utils.texts import BAD_WORDS, BAN_WORDS, VPN_PHRASES, TAPIR_PHRASES, ALLOWED_DOMAINS, REFUND_KEYWORDS, SAFE_PHRASES, MUTE_SHORT_PHRASES, MUTE_CRITICAL_PHRASES
from utils.funcs import delete_later, log_to_owner, send_morning_voice
from handlers.ai import handle_ai_request, veteran_reply

router = Router()

async def verification_timer(chat_id, user_id, username, msg_id):
    try:
        await asyncio.sleep(180)
        remind = await bot.send_message(chat_id, f"@{username}, подтверди, что ты не бот!", reply_to_message_id=msg_id)
        if user_id in PENDING_VERIFICATION: PENDING_VERIFICATION[user_id]['remind_msg_id'] = remind.message_id
        await asyncio.sleep(120)
        await bot.ban_chat_member(chat_id, user_id)
        await bot.send_message(chat_id, f"@{username} изгнан (Bot).")
        try: await bot.delete_message(chat_id, msg_id)
        except: pass
    except: pass
    finally:
        if user_id in PENDING_VERIFICATION: del PENDING_VERIFICATION[user_id]

@router.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        if user.is_bot: continue
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛡 Я НЕ БОТ", callback_data=f"verify_{user.id}")]])
        msg = await message.answer(f"@{user.first_name}, нажми кнопку или напиши сообщение за 5 минут!", reply_markup=kb)
        task = asyncio.create_task(verification_timer(message.chat.id, user.id, user.first_name, msg.message_id))
        PENDING_VERIFICATION[user.id] = {'task': task, 'msg_id': msg.message_id, 'remind_msg_id': None}

@router.callback_query(F.data.startswith("verify_"))
async def verify_handler(callback: types.CallbackQuery):
    if callback.from_user.id != int(callback.data.split("_")[1]): await callback.answer("Не твое!"); return
    uid = callback.from_user.id
    if uid in PENDING_VERIFICATION:
        PENDING_VERIFICATION[uid]['task'].cancel()
        try: await bot.delete_message(callback.message.chat.id, PENDING_VERIFICATION[uid]['msg_id'])
        except: pass
        del PENDING_VERIFICATION[uid]
        await callback.message.answer(f"Допуск получен, @{callback.from_user.first_name}.")

@router.message(F.is_automatic_forward)
async def auto_comment(message: types.Message):
    # Логика с PROCESSED_ALBUMS из оригинала
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Правила", url=LINK_RULES)]])
    await message.reply("Загрузка навигации...", reply_markup=kb)

@router.message(Command("lw", "lastword"))
async def lastword_handler(message: types.Message):
    if random.randint(1, 4) == 1:
        # Логика мута
        mute_min = 30 if random.randint(1, 5) == 5 else 15
        try:
            await message.chat.restrict(user_id=message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(minutes=mute_min))
            await message.reply(f"💥 Выстрел! Ты в муте на {mute_min} мин.")
        except: await message.reply("Я бы замутил, но прав нет.")
    else:
        await message.reply(random.choice(SAFE_PHRASES))

@router.message()
async def main_message_handler(message: types.Message):
    global LAST_MESSAGE_TIME
    LAST_MESSAGE_TIME = datetime.now()
    
    if not message.text: return
    text = message.text.lower()
    user = message.from_user
    
    # 1. Теневой бан
    if user.id in SILENT_MODE_USERS:
        try: await message.delete(); return
        except: pass

    # 2. Верификация сообщением
    if user.id in PENDING_VERIFICATION:
        PENDING_VERIFICATION[user.id]['task'].cancel()
        del PENDING_VERIFICATION[user.id]

    # 3. Фильтры слов (Бан/Удаление)
    for w in BAN_WORDS:
        if w in text:
            await message.chat.ban(user.id)
            await message.delete(); return
    for w in BAD_WORDS:
        if w in text:
            await message.delete(); await message.answer(f"@{user.first_name}, не ругайся."); return

    # 4. Ссылки
    urls = re.findall(r"https?://[^\s]+", text)
    if urls:
        allowed = any(d in u for u in urls for d in ALLOWED_DOMAINS)
        if not allowed: await message.delete(); return

    # 5. Реакции и триггеры
    if "vpn" in text or "впн" in text: await message.reply(random.choice(VPN_PHRASES))
    if "тапир" in text: await message.reply(random.choice(TAPIR_PHRASES))
    
    # 6. AI (если тег)
    bot_me = await bot.get_me()
    if f"@{bot_me.username}" in message.text:
        clean = message.text.replace(f"@{bot_me.username}", "").strip()
        await handle_ai_request(message, clean)
        return

    # 7. Рандомный ответ ветерана
    if random.randint(1, 500) == 1:
        await veteran_reply(message)

    # Лог
    CHAT_HISTORY.append(f"{user.first_name}: {message.text[:100]}")
    if len(CHAT_HISTORY) > 150: CHAT_HISTORY.pop(0)
