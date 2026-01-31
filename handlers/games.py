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

# Подгружаем дуэли из файла при запуске
try:
    loaded = load_duels()
    ACTIVE_DUELS.update(loaded)
except:
    pass

# --- КОМАНДА ВЫЗОВА ---
@router.message(Command("duel"))
async def duel_command(message: types.Message):
    if not message.reply_to_message:
        msg = await message.reply("⚔️ Чтобы вызвать на дуэль, ответь на сообщение соперника.")
        asyncio.create_task(delete_later(msg, 5)); return

    attacker = message.from_user
    defender = message.reply_to_message.from_user

    if defender.is_bot or defender.id == attacker.id:
        msg = await message.reply("Найди себе живого противника."); return

    att_name = f"@{attacker.username}" if attacker.username else attacker.first_name
    def_name = f"@{defender.username}" if defender.username else defender.first_name

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔫 Принять вызов", callback_data=f"duel_start|{attacker.id}|{defender.id}"),
        InlineKeyboardButton(text="🏳️ Сбежать", callback_data=f"duel_decline")
    ]])

    await message.answer(
        f"<b>⚔️ ГОРНИЛО: ДУЭЛЬ!</b>\n\n"
        f"<b>🔴 Страж:</b> {att_name}\n"
        f"<b>🔵 Страж:</b> {def_name}\n\n"
        f"<b>{def_name}</b>, ты принимаешь бой?",
        reply_markup=kb
    )

# --- ОБНОВЛЕНИЕ ИНТЕРФЕЙСА ---
async def update_duel_message(callback: types.CallbackQuery, game_id):
    if game_id not in ACTIVE_DUELS: return
    game = ACTIVE_DUELS[game_id]
    
    # Защита от флуда кнопками
    now = datetime.now()
    if (now - game.get("last_update", datetime.min)).total_seconds() < 0.8: return
    game["last_update"] = now
    
    p1, p2 = game["p1"], game["p2"]
    def get_hp_bar(hp): return "▓" * int(hp / 10) + "░" * (10 - int(hp / 10))
    
    curr = p1 if game["turn"] == p1["id"] else p2
    ru_cls = {"hunter": "🐍", "warlock": "🔮", "titan": "🛡"}
    
    status_effects = ""
    if p1["buff_def"] > 0: status_effects += f"\n🛡 {p1['name']}: Щит {p1['buff_def']}"
    if p2["buff_def"] > 0: status_effects += f"\n🛡 {p2['name']}: Щит {p2['buff_def']}"

    text = (
        f"⚔️ <b>{ru_cls.get(p1['class'], '?')} vs {ru_cls.get(p2['class'], '?')}</b>\n\n"
        f"🔴 <b>{p1['name']}</b>: {p1['hp']} HP\n[{get_hp_bar(p1['hp'])}]\n"
        f"🔵 <b>{p2['name']}</b>: {p2['hp']} HP\n[{get_hp_bar(p2['hp'])}]\n\n"
        f"📜 <i>Лог: {game['log']}</i>{status_effects}\n\n"
        f"👉 <b>Ход:</b> {curr['name']}"
    )

    btns = []
    wpn_t = "♠️ Ace" if curr["weapon"] == "ace" else "🤠 Last Word"
    weapon_btn = InlineKeyboardButton(text=wpn_t, callback_data="duel_shoot_primary")

    if curr["class"] == "hunter":
        btns = [[weapon_btn, InlineKeyboardButton(text="🔥 Сияние", callback_data="duel_buff_radiant")],
                [InlineKeyboardButton(text="🔫 Golden Gun", callback_data="duel_gg")]]
    elif curr["class"] == "warlock":
        btns = [[weapon_btn, InlineKeyboardButton(text="🌀 Пожирание", callback_data="duel_buff_devour")],
                [InlineKeyboardButton(text="🟣 Nova Bomb", callback_data="duel_nova")]]
    elif curr["class"] == "titan":
        btns = [[weapon_btn, InlineKeyboardButton(text="🛡 Усиление", callback_data="duel_buff_amplify")],
                [InlineKeyboardButton(text="⚡ Thundercrash", callback_data="duel_crash")]]

    try: await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    except: pass

# --- ВЫБОР И БОЙ (ПОЛНАЯ ЛОГИКА) ---
@router.callback_query(F.data.startswith(("pick_", "duel_")))
async def duel_handler(callback: types.CallbackQuery):
    data = callback.data.split("|")
    action = data[0]
    game_id = callback.message.message_id

    # 1. Начало / Отмена
    if action == "duel_decline":
        ACTIVE_DUELS.pop(game_id, None)
        await callback.message.edit_text("🏳️ Дуэль отменена."); return

    if action == "duel_start":
        p1_id, p2_id = int(data[1]), int(data[2])
        if callback.from_user.id != p2_id: return
        
        ACTIVE_DUELS[game_id] = {
            "p1": {"id": p1_id, "name": "Игрок 1", "hp": 100, "class": None, "weapon": None, "ace_streak": 0, "buff_dmg": 0, "buff_heal": False, "buff_def": 0},
            "p2": {"id": p2_id, "name": "Игрок 2", "hp": 100, "class": None, "weapon": None, "ace_streak": 0, "buff_dmg": 0, "buff_heal": False, "buff_def": 0},
            "state": "choosing", "log": "Выбор снаряжения...", "lock": asyncio.Lock()
        }
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐍 Хантер", callback_data="pick_class_hunter"), InlineKeyboardButton(text="🔮 Варлок", callback_data="pick_class_warlock"), InlineKeyboardButton(text="🛡 Титан", callback_data="pick_class_titan")],
            [InlineKeyboardButton(text="♠️ Ace", callback_data="pick_weapon_ace"), InlineKeyboardButton(text="🤠 LW", callback_data="pick_weapon_lw")],
            [InlineKeyboardButton(text="🎲 Рандом", callback_data="pick_random")]
        ])
        await callback.message.edit_text("🎒 <b>СБОРКА БИЛДА</b>\nВыбери класс и оружие:", reply_markup=kb); return

    if game_id not in ACTIVE_DUELS: return
    game = ACTIVE_DUELS[game_id]

    # 2. Обработка выбора (Pick)
    if action.startswith("pick_"):
        user_id = callback.from_user.id
        p = game["p1"] if user_id == game["p1"]["id"] else game["p2"] if user_id == game["p2"]["id"] else None
        if not p: return

        if "class" in action: p["class"] = action.split("_")[2]
        elif "weapon" in action: p["weapon"] = action.split("_")[2]
        elif "random" in action:
            p["class"] = random.choice(["hunter", "warlock", "titan"])
            p["weapon"] = random.choice(["ace", "lw"])

        if game["p1"]["class"] and game["p1"]["weapon"] and game["p2"]["class"] and game["p2"]["weapon"]:
            game["state"] = "fighting"
            game["turn"] = random.choice([game["p1"]["id"], game["p2"]["id"]])
            game["log"] = "⚔️ Да начнется битва!"
            await update_duel_message(callback, game_id)
        else:
            await callback.answer("Принято!")
        return

    # 3. Боевые действия
    async with game["lock"]:
        if callback.from_user.id != game["turn"]: 
            await callback.answer("Не твой ход!", show_alert=True); return
        
        sh, tg = (game["p1"], game["p2"]) if callback.from_user.id == game["p1"]["id"] else (game["p2"], game["p1"])
        
        damage = 0
        log_msg = ""

        # Логика выстрела (Ace/LW)
        if action == "duel_shoot_primary":
            if sh["weapon"] == "ace":
                roll = random.randint(1, 100)
                if sh["ace_streak"] == 1 and roll <= 10:
                    damage = 50; log_msg = f"💀 <b>MEMENTO MORI!</b> {sh['name']} попал в голову! (50)"; sh["ace_streak"] = 0
                elif roll <= 50:
                    damage = 25; log_msg = f"💥 {sh['name']} попал из Туза! (25)"; sh["ace_streak"] = 1
                else:
                    log_msg = f"💨 {sh['name']} промахнулся из Туза."; sh["ace_streak"] = 0
            else: # LW
                hits = 0
                for _ in range(8):
                    if random.randint(1, 100) <= 34: damage += 5; hits += 1
                log_msg = f"🤠 <b>Fan Fire!</b> {hits} попаданий из LW! ({damage})"

        # Логика абилок
        elif action == "duel_buff_radiant":
            sh["buff_dmg"] = 10; log_msg = f"🔥 {sh['name']} стал <b>Сияющим</b>! (+10 урона)"
        elif action == "duel_buff_devour":
            sh["buff_heal"] = True; log_msg = f"🌀 {sh['name']} активировал <b>Пожирание</b>!"
        elif action == "duel_buff_amplify":
            sh["buff_def"] = 10; log_msg = f"🛡 {sh['name']} получил щит!"

        # Применение урона и баффов
        if damage > 0:
            if sh["buff_dmg"] > 0: damage += 10; sh["buff_dmg"] = 0
            if tg["buff_def"] > 0:
                block = min(damage, tg["buff_def"])
                damage -= block; tg["buff_def"] -= block
            tg["hp"] -= damage
            if sh["buff_heal"]: sh["hp"] = min(100, sh["hp"] + 10); sh["buff_heal"] = False

        game["log"] = log_msg
        
        if tg["hp"] <= 0:
            tg["hp"] = 0
            update_duel_stats(sh["id"], True); update_duel_stats(tg["id"], False)
            await callback.message.edit_text(f"🏆 <b>ПОБЕДА!</b>\n\n{log_msg}\n💀 {tg['name']} пал в бою."); del ACTIVE_DUELS[game_id]
        else:
            game["turn"] = tg["id"]
            save_duels(ACTIVE_DUELS)
            await update_duel_message(callback, game_id)
            await callback.answer()
