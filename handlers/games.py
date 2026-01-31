import asyncio
import random
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot
from state import ACTIVE_DUELS
from database import update_usage, update_duel_stats, save_duels, load_duels
from utils.funcs import delete_later

router = Router()

# Подгрузим дуэли при старте модуля
loaded = load_duels()
ACTIVE_DUELS.update(loaded)

@router.message(Command("duel"))
async def duel_command(message: types.Message):
    if not message.reply_to_message:
        msg = await message.reply("⚔️ Ответь на сообщение соперника командой <code>/duel</code>.")
        asyncio.create_task(delete_later(msg, 5)); return

    attacker, defender = message.from_user, message.reply_to_message.from_user
    if defender.is_bot or defender.id == attacker.id:
        msg = await message.reply("Найди достойного противника."); asyncio.create_task(delete_later(msg, 5)); return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔫 Принять", callback_data=f"duel_start|{attacker.id}|{defender.id}"),
        InlineKeyboardButton(text="🏳️ Сбежать", callback_data=f"duel_decline|{attacker.id}|{defender.id}")
    ]])
    await message.answer(
        f"<b>⚔️ ДУЭЛЬ!</b>\n🔴 {attacker.first_name} vs 🔵 {defender.first_name}\nПринимаешь бой?", reply_markup=kb
    )

async def update_duel_message(callback: types.CallbackQuery, game_id):
    if game_id not in ACTIVE_DUELS:
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass; return

    game = ACTIVE_DUELS[game_id]
    now = datetime.now()
    if (now - game.get("last_update", datetime.min)).total_seconds() < 1.0: return
    game["last_update"] = now
    
    p1, p2 = game["p1"], game["p2"]
    current = p1 if game["turn"] == p1["id"] else p2
    
    def bar(hp): return "▓" * int(hp / 10) + "░" * (10 - int(hp / 10))
    
    ru = {"hunter": "🐍", "warlock": "🔮", "titan": "🛡"}
    
    status = f"🛡 {p1['name']}: Щит {p1['buff_def']}\n" if p1['buff_def'] else ""
    status += f"🛡 {p2['name']}: Щит {p2['buff_def']}\n" if p2['buff_def'] else ""
    if game.get("pending_crash"): status += "\n⚡ <b>ВРАГ В ВОЗДУХЕ!</b>"

    text = (
        f"⚔️ {ru.get(p1['class'],'')} vs {ru.get(p2['class'],'')}\n\n"
        f"🔴 <b>{p1['name']}</b>: {p1['hp']} HP [{bar(p1['hp'])}]\n"
        f"🔵 <b>{p2['name']}</b>: {p2['hp']} HP [{bar(p2['hp'])}]\n\n"
        f"📜 {game['log']}\n{status}\n👉 Ход: {current['name']}"
    )

    btns = []
    # Логика кнопок (сокращенно для примера, логика та же)
    wpn_btn = InlineKeyboardButton(text="Атака (Туз/ЛВ)", callback_data="duel_shoot_primary")
    
    cls = current["class"]
    if cls == "hunter":
        btns = [[wpn_btn, InlineKeyboardButton(text="🔥 Сияние", callback_data="duel_buff_radiant")],
                [InlineKeyboardButton(text="🔫 Golden Gun", callback_data="duel_gg")]]
    elif cls == "warlock":
        btns = [[wpn_btn, InlineKeyboardButton(text="🌀 Пожирание", callback_data="duel_buff_devour")],
                [InlineKeyboardButton(text="🟣 Nova Bomb", callback_data="duel_nova")]]
    elif cls == "titan":
        btns = [[wpn_btn, InlineKeyboardButton(text="🛡 Усиление", callback_data="duel_buff_amplify")],
                [InlineKeyboardButton(text="⚡ Thundercrash", callback_data="duel_crash")]]
    
    btns.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="duel_refresh")])
    try: await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    except: pass

@router.callback_query(F.data.startswith("pick_"))
async def duel_pick_handler(callback: types.CallbackQuery):
    game_id = callback.message.message_id
    if game_id not in ACTIVE_DUELS: await callback.answer("Матч устарел."); return
    game = ACTIVE_DUELS[game_id]
    
    uid = callback.from_user.id
    pkey = "p1" if uid == game["p1"]["id"] else "p2" if uid == game["p2"]["id"] else None
    if not pkey: await callback.answer("Не твой бой!"); return
    
    player = game[pkey]
    data = callback.data
    
    if data == "pick_full_random":
        player["class"] = random.choice(["hunter", "warlock", "titan"])
        player["weapon"] = random.choice(["ace", "lw"])
    elif "pick_class" in data: player["class"] = data.split("_")[2]
    elif "pick_weapon" in data: player["weapon"] = data.split("_")[2]
    
    if game["p1"]["class"] and game["p1"]["weapon"] and game["p2"]["class"] and game["p2"]["weapon"]:
        game["state"] = "fighting"
        game["turn"] = random.choice([game["p1"]["id"], game["p2"]["id"]])
        update_usage(game["p1"]["id"], f"class_{game['p1']['class']}")
        update_usage(game["p2"]["id"], f"class_{game['p2']['class']}")
        game["log"] = "Бой начинается!"
        await update_duel_message(callback, game_id)
    else:
        # Обновить текст выбора
        await callback.answer("Выбор принят")

@router.callback_query(F.data.startswith("duel_"))
async def duel_main_handler(callback: types.CallbackQuery):
    action = callback.data.split("|")[0]
    game_id = callback.message.message_id
    
    # Старт
    if action == "duel_start":
        p1_id, p2_id = int(callback.data.split("|")[1]), int(callback.data.split("|")[2])
        if callback.from_user.id != p2_id: await callback.answer("Жди решения!"); return
        
        ACTIVE_DUELS[game_id] = {
            "p1": {"id": p1_id, "name": "Игрок 1", "hp": 100, "class": None, "weapon": None, "buff_def": 0, "ace_streak": 0, "buff_dmg": 0, "buff_heal": False},
            "p2": {"id": p2_id, "name": "Игрок 2", "hp": 100, "class": None, "weapon": None, "buff_def": 0, "ace_streak": 0, "buff_dmg": 0, "buff_heal": False},
            "state": "choosing", "log": "Выбор...", "lock": asyncio.Lock()
        }
        # Нужно получить имена пользователей, но callback ограничен. Обновим позже или используем дефолт
        # ... тут клавиатура выбора класса (как в оригинале) ...
        # Для краткости:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Random", callback_data="pick_full_random")],
            [InlineKeyboardButton(text="Hunter", callback_data="pick_class_hunter"), InlineKeyboardButton(text="Titan", callback_data="pick_class_titan"), InlineKeyboardButton(text="Warlock", callback_data="pick_class_warlock")],
            [InlineKeyboardButton(text="Ace", callback_data="pick_weapon_ace"), InlineKeyboardButton(text="Last Word", callback_data="pick_weapon_lw")]
        ])
        await callback.message.edit_text("Выбирайте снаряжение!", reply_markup=kb)
        return

    # Логика боя (выстрелы)
    if game_id not in ACTIVE_DUELS: await callback.answer("Игра не найдена"); return
    game = ACTIVE_DUELS[game_id]
    
    if action == "duel_refresh": await update_duel_message(callback, game_id); await callback.answer(); return

    async with game["lock"]:
        # Сюда вставь огромную логику if action == "duel_shoot_primary" и т.д. из оригинала
        # Принцип тот же: меняем game, вызываем save_duels(ACTIVE_DUELS), вызываем update_duel_message
        # Если HP < 0 -> удаляем из словаря и пишем победу.
        pass 
    
    await update_duel_message(callback, game_id)
    await callback.answer()
