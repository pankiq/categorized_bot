import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions

from config import bot, OWNER_ID
from state import SILENT_MODE_USERS, TOURNAMENT_ACTIVE, TOURNAMENT_MAX_PLAYERS, TOURNAMENT_PLAYERS, TOURNAMENT_USERNAMES
from utils.funcs import delete_later, log_to_owner
from utils.texts import ADMIN_MUTE_PHRASES, UNMUTE_PHRASES

router = Router()

# --- MUTE / UNMUTE / AMUTE ---
@router.message(Command("amute"))
async def amute_command(message: types.Message):
    try: await message.delete()
    except: pass

    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]: return

    if not message.reply_to_message:
        msg = await message.answer("⚠️ Ответь на сообщение того, кого хочешь заглушить.")
        asyncio.create_task(delete_later(msg, 5))
        return

    target = message.reply_to_message.from_user
    if target.id == message.from_user.id: return

    if target.id not in SILENT_MODE_USERS:
        SILENT_MODE_USERS.append(target.id)
        await message.answer(f"🤫 <b>{target.first_name}</b> отправлен в теневой бан.")
    else:
        msg = await message.answer(f"{target.first_name} уже в муте.")
        asyncio.create_task(delete_later(msg, 5))

@router.message(Command("unamute"))
async def unamute_command(message: types.Message):
    try: await message.delete()
    except: pass

    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]: return
    if not message.reply_to_message: return

    target_id = message.reply_to_message.from_user.id
    if target_id in SILENT_MODE_USERS:
        SILENT_MODE_USERS.remove(target_id)
        msg = await message.answer(f"🔊 <b>{message.reply_to_message.from_user.first_name}</b> снова слышен.")
        asyncio.create_task(delete_later(msg, 10))

@router.message(Command("mute"))
async def admin_mute_command(message: types.Message, command: CommandObject):
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]: return

    mute_minutes = 15
    args = command.args.split() if command.args else []
    for arg in args:
        if arg.isdigit():
            mute_minutes = int(arg)
            break
    
    target_user = message.reply_to_message.from_user if message.reply_to_message else None
    if not target_user:
        msg = await message.answer("⚠️ Reply (Ответить) на сообщение нарушителя.\nПример: <code>/mute</code> 30")
        asyncio.create_task(delete_later(msg, 10)); return

    try:
        unmute_time = datetime.now() + timedelta(minutes=mute_minutes)
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=unmute_time
        )
        username = target_user.username or target_user.first_name
        phrase = random.choice(ADMIN_MUTE_PHRASES).format(time=mute_minutes).replace("@username", f"@{username}")
        await message.answer(phrase)
    except Exception as e:
        await log_to_owner(f"❌ Ошибка мута: {e}")

@router.message(Command("unmute"))
async def admin_unmute_command(message: types.Message):
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]: return 
    if not message.reply_to_message: return

    target_user = message.reply_to_message.from_user
    username = target_user.username or target_user.first_name
    try:
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True),
            until_date=datetime.now()
        )
        text = random.choice(UNMUTE_PHRASES).replace("@username", f"@{username}")
        await message.answer(text)
    except Exception as e:
        await log_to_owner(f"❌ Ошибка размута: {e}")

# --- ТУРНИР ---
@router.message(Command("startcup"))
async def start_cup_command(message: types.Message, command: CommandObject):
    if message.from_user.id != OWNER_ID: return
    args = command.args
    if not args or not args.isdigit():
        await message.reply("Укажи количество участников. Пример: `/startcup 8`"); return

    global TOURNAMENT_ACTIVE, TOURNAMENT_MAX_PLAYERS, TOURNAMENT_PLAYERS, TOURNAMENT_USERNAMES
    TOURNAMENT_ACTIVE = True
    TOURNAMENT_MAX_PLAYERS = int(args)
    TOURNAMENT_PLAYERS = []
    TOURNAMENT_USERNAMES = []

    await message.answer(f"<b>🏆 РЕГИСТРАЦИЯ НА ТУРНИР ОТКРЫТА!</b>\nНужно стражей: {args}\nКоманда: <code>/cup</code>")

@router.message(Command("cup"))
async def join_cup_command(message: types.Message):
    global TOURNAMENT_ACTIVE
    if not TOURNAMENT_ACTIVE:
        msg = await message.reply("Сейчас не ведется набор в турнир.")
        asyncio.create_task(delete_later(msg, 5)); return

    user_id = message.from_user.id
    if user_id in TOURNAMENT_PLAYERS:
        msg = await message.reply("Ты уже в списке."); asyncio.create_task(delete_later(msg, 5)); return

    TOURNAMENT_PLAYERS.append(user_id)
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    TOURNAMENT_USERNAMES.append(username)
    
    current = len(TOURNAMENT_PLAYERS)
    if current < TOURNAMENT_MAX_PLAYERS:
        await message.answer(f"✅ {username} записан! ({current}/{TOURNAMENT_MAX_PLAYERS})")
    else:
        TOURNAMENT_ACTIVE = False
        random.shuffle(TOURNAMENT_USERNAMES)
        pairs_text = ""
        for i in range(0, len(TOURNAMENT_USERNAMES), 2):
            p1 = TOURNAMENT_USERNAMES[i]
            if i + 1 < len(TOURNAMENT_USERNAMES):
                pairs_text += f"⚔️ {p1} vs {TOURNAMENT_USERNAMES[i+1]}\n"
            else:
                pairs_text += f"⚠ Без пары: {p1}.\n"
        await message.answer(f"🚫 <b>НАБОР ЗАКРЫТ! Сетка:</b>\n\n{pairs_text}")
