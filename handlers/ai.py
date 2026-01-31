from aiogram import Router, types, F
from aiogram.filters import Command
from datetime import datetime, timedelta

from config import client, bot, AI_SYSTEM_PROMPT
from state import AI_COOLDOWN_TIME, SUMMARY_COOLDOWN_TIME, CHAT_HISTORY
from utils.funcs import delete_later, log_to_owner

router = Router()

@router.message(Command("summary"))
async def summary_command(message: types.Message):
    global SUMMARY_COOLDOWN_TIME
    if datetime.now() < SUMMARY_COOLDOWN_TIME:
        msg = await message.reply("Подожди немного, я недавно уже делал отчет.")
        asyncio.create_task(delete_later(msg, 10)); return

    if len(CHAT_HISTORY) < 5:
        await message.answer("Архивы пусты."); return

    history_text = "\n".join(CHAT_HISTORY)
    prompt = "Прочитай лог чата и кратко (3-4 предложения) перескажи, о чем говорили. С юмором Destiny 2."
    
    try:
        await bot.send_chat_action(message.chat.id, action="typing")
        response = await client.chat.completions.create(
            model="sonar",
            messages=[{"role": "system", "content": AI_SYSTEM_PROMPT}, {"role": "user", "content": history_text}],
            temperature=0.8, max_tokens=300
        )
        await message.reply(f"<b>📄 ОТЧЕТ:</b>\n\n{response.choices[0].message.content}")
        SUMMARY_COOLDOWN_TIME = datetime.now() + timedelta(minutes=15)
    except Exception as e:
        await log_to_owner(f"❌ Ошибка Summary: {e}")

async def handle_ai_request(message: types.Message, clean_text: str):
    global AI_COOLDOWN_TIME
    if datetime.now() < AI_COOLDOWN_TIME:
        msg = await message.reply("Я занят, лайт поднимаю. Подожди 5 минут.")
        asyncio.create_task(delete_later(msg, 5)); return

    try:
        await bot.send_chat_action(message.chat.id, action="typing")
        response = await client.chat.completions.create(
            model="sonar",
            messages=[{"role": "system", "content": AI_SYSTEM_PROMPT}, {"role": "user", "content": clean_text}],
            temperature=0.8, max_tokens=500
        )
        await message.reply(response.choices[0].message.content)
        AI_COOLDOWN_TIME = datetime.now() + timedelta(minutes=5)
    except Exception as e:
        await log_to_owner(f"❌ Ошибка AI: {e}")

async def veteran_reply(message: types.Message):
    VETERAN_PROMPT = "Ты ветеран Destiny 2 с 10к часов. Ответь кратко и дерзко на сообщение нуба с сарказмом."
    try:
        await bot.send_chat_action(message.chat.id, action="typing")
        response = await client.chat.completions.create(
            model="sonar",
            messages=[{"role": "system", "content": VETERAN_PROMPT}, {"role": "user", "content": f"Сообщение: {message.text}"}],
            temperature=1, max_tokens=100
        )
        await message.reply(response.choices[0].message.content)
    except Exception as e:
        await log_to_owner(f"❌ Veteran Error: {e}")
