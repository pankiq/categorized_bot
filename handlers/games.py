Да, именно так. Вместо `pass` и комментариев нужно вставить ту самую «огромную» логику обработки выстрелов, баффов и ульты.

Я собрал для тебя **полный код файла `handlers/games.py**`, включая всю боевую математику из твоего оригинального файла. Просто скопируй этот код целиком и замени им содержимое `handlers/games.py`.

### Полный код `handlers/games.py`

```python
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
try:
    loaded = load_duels()
    ACTIVE_DUELS.update(loaded)
except Exception as e:
    print(f"Ошибка загрузки дуэлей: {e}")

# --- КОМАНДА ВЫЗОВА ---
@router.message(Command("duel"))
async def duel_command(message: types.Message):
    if not message.reply_to_message:
        msg = await message.reply("⚔️ Чтобы вызвать на дуэль, ответь на сообщение соперника командой <code>/duel</code>.")
        asyncio.create_task(delete_later(msg, 5)); return

    attacker = message.from_user
    defender = message.reply_to_message.from_user

    if defender.is_bot or defender.id == attacker.id:
        msg = await message.reply("Найди себе достойного противника (живого человека).")
        asyncio.create_task(delete_later(msg, 5)); return

    # Имена
    att_name = f"@{attacker.username}" if attacker.username else attacker.first_name
    def_name = f"@{defender.username}" if defender.username else defender.first_name

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔫 Принять вызов", callback_data=f"duel_start|{attacker.id}|{defender.id}"),
        InlineKeyboardButton(text="🏳️ Сбежать", callback_data=f"duel_decline|{attacker.id}|{defender.id}")
    ]])

    await message.answer(
        f"<b>⚔️ ГОРНИЛО: ДУЭЛЬ!</b>\n\n"
        f"<b>🔴 Страж №1:</b> {att_name}\n"
        f"<b>🔵 Страж №2:</b> {def_name}\n\n"
        f"<b>📜 Сетапы классов:</b>\n"
        f"🔥 - Ханты: ГГ & Сияние\n"
        f"🔮 - Варлоки: Нова & Пожирание\n"
        f"☄️ - Титаны: ТКраш & Усиление\n"
        f"<b>🔫 На выбор:</b> Туз/ЛВ.\n\n"
        f"<b>{def_name}</b>, ты принимаешь бой?",
        reply_markup=kb
    )

# --- ОБНОВЛЕНИЕ СООБЩЕНИЯ (ИНТЕРФЕЙС) ---
async def update_duel_message(callback: types.CallbackQuery, game_id):
    if game_id not in ACTIVE_DUELS:
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass; return

    game = ACTIVE_DUELS[game_id]
    
    # Анти-флуд обновлением (не чаще раза в секунду)
    now = datetime.now()
    last = game.get("last_update", datetime.min)
    if (now - last).total_seconds() < 1.0: return
    game["last_update"] = now
    
    # Визуализация HP
    def get_hp_bar(hp):
        blocks = int(hp / 10) 
        return "▓" * blocks + "░" * (10 - blocks)

    p1 = game["p1"]
    p2 = game["p2"]
    
    current_player = p1 if game["turn"] == p1["id"] else p2
    current_class = current_player["class"]
    current_weapon = current_player["weapon"]
    
    ru_classes = {"hunter": "🐍", "warlock": "🔮", "titan": "🛡"}
    
    # Статусы (щиты, полет)
    def_status = ""
    if p1["buff_def"] > 0: def_status += f"\n🛡 {p1['name']}: Щит {p1['buff_def']} HP"
    if p2["buff_def"] > 0: def_status += f"\n🛡 {p2['name']}: Щит {p2['buff_def']} HP"
    
    flying_status = "\n⚡ <b>ВРАГ В ВОЗДУХЕ! СБЕЙ ЕГО!</b>" if game.get("pending_crash") else ""

    text = (
        f"⚔️ <b>{ru_classes.get(p1['class'], '?')} vs {ru_classes.get(p2['class'], '?')}</b>\n\n"
        f"🔴 <b>{p1['name']}</b>: {p1['hp']} HP\n[{get_hp_bar(p1['hp'])}]\n\n"
        f"🔵 <b>{p2['name']}</b>: {p2['hp']} HP\n[{get_hp_bar(p2['hp'])}]\n\n"
        f"📜 <i>Лог: {game['log']}</i>{flying_status}{def_status}\n\n"
        f"👉 <b>Ход:</b> {current_player['name']} ({ru_classes.get(current_class, '')})"
    )

    # Кнопки
    buttons = []
    
    # Оружие
    wpn_text = "♠️ Ace (50%)" if current_weapon == "ace" else "🤠 Last Word (Burst)"
    weapon_btn = InlineKeyboardButton(text=wpn_text, callback_data="duel_shoot_primary")

    # Сборка под класс
    if current_class == "hunter":
        buttons = [
            [weapon_btn, InlineKeyboardButton(text="🔥 Сияние (+Dmg)", callback_data="duel_buff_radiant")],
            [InlineKeyboardButton(text="🔫 Golden Gun (9%)", callback_data="duel_gg")]
        ]
    elif current_class == "warlock":
        buttons = [
            [weapon_btn, InlineKeyboardButton(text="🌀 Пожирание (+Heal)", callback_data="duel_buff_devour")],
            [InlineKeyboardButton(text="🟣 Nova Bomb (14%)", callback_data="duel_nova")]
        ]
    elif current_class == "titan":
        buttons = [
            [weapon_btn, InlineKeyboardButton(text="🛡 Усиление (Щит)", callback_data="duel_buff_amplify")],
            [InlineKeyboardButton(text="⚡ Thundercrash (22%)", callback_data="duel_crash")]
        ]

    buttons.append([InlineKeyboardButton(text="🔄 Обновить (если зависло)", callback_data="duel_refresh")])
    
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception as e:
        if "Flood" in str(e): await asyncio.sleep(1)

# --- ВЫБОР КЛАССА / ОРУЖИЯ ---
@router.callback_query(F.data.startswith("pick_"))
async def duel_pick_handler(callback: types.CallbackQuery):
    game_id = callback.message.message_id
    if game_id not in ACTIVE_DUELS:
        await callback.answer("Матч устарел.", show_alert=True); return

    game = ACTIVE_DUELS[game_id]
    user_id = callback.from_user.id
    data = callback.data

    player_key = "p1" if user_id == game["p1"]["id"] else "p2" if user_id == game["p2"]["id"] else None
    if not player_key:
        await callback.answer("Ты не участвуешь!", show_alert=True); return

    player = game[player_key]

    if data == "pick_full_random":
        if player["class"] and player["weapon"]:
            await callback.answer("Ты уже готов!", show_alert=True); return
        player["class"] = random.choice(["hunter", "warlock", "titan"])
        player["weapon"] = random.choice(["ace", "lw"])
        await callback.answer("Случайный билд выбран!")
    elif "pick_class" in data:
        player["class"] = data.split("_")[2]
        await callback.answer(f"Класс: {player['class']}")
    elif "pick_weapon" in data:
        if not player["class"]:
            await callback.answer("Сначала выбери класс!", show_alert=True); return
        player["weapon"] = data.split("_")[2]
        await callback.answer(f"Оружие: {player['weapon']}")

    # Если оба готовы -> СТАРТ
    if game["p1"]["class"] and game["p1"]["weapon"] and game["p2"]["class"] and game["p2"]["weapon"]:
        game["state"] = "fighting"
        game["turn"] = random.choice([game["p1"]["id"], game["p2"]["id"]])
        
        # Обновляем статистику использования
        update_usage(game["p1"]["id"], f"class_{game['p1']['class']}")
        update_usage(game["p2"]["id"], f"class_{game['p2']['class']}")
        
        c1, c2 = game["p1"]["class"].upper(), game["p2"]["class"].upper()
        game["log"] = f"⚔️ {c1} vs {c2}! Бой начинается!"
        
        save_duels(ACTIVE_DUELS)
        await update_duel_message(callback, game_id)
    else:
        # Обновляем статус выбора
        def get_status(p):
            if not p["class"]: return "Ждет выбора класса..."
            if not p["weapon"]: return f"{p['class'].capitalize()} (Ждет оружия...)"
            return "✅ ГОТОВ"
            
        text = (
            f"🎒 <b>ВЫБОР СНАРЯЖЕНИЯ</b>\n\n"
            f"👤 <b>{game['p1']['name']}:</b> {get_status(game['p1'])}\n"
            f"👤 <b>{game['p2']['name']}:</b> {get_status(game['p2'])}\n\n"
            f"1. Выбери Класс\n2. Выбери Оружие"
        )
        try: await callback.message.edit_text(text, reply_markup=callback.message.reply_markup)
        except: pass
        await callback.answer()

# --- ОСНОВНАЯ ЛОГИКА БОЯ ---
@router.callback_query(F.data.startswith("duel_"))
async def duel_main_handler(callback: types.CallbackQuery):
    data_parts = callback.data.split("|")
    action = data_parts[0]
    game_id = callback.message.message_id
    
    # 1. Поиск игры (в памяти или файле)
    if game_id not in ACTIVE_DUELS:
        try:
            saved = load_duels()
            if game_id in saved: ACTIVE_DUELS[game_id] = saved[game_id]
        except: pass

    # 2. Обработка кнопок старта/отказа (когда игры еще нет или она только создается)
    if action == "duel_decline":
        if game_id in ACTIVE_DUELS: del ACTIVE_DUELS[game_id]
        await callback.message.edit_text("🏳️ <b>Дуэль отменена.</b>"); return

    if action == "duel_start":
        p1_id, p2_id = int(data_parts[1]), int(data_parts[2])
        if callback.from_user.id != p2_id: await callback.answer("Жди решения!", show_alert=True); return
        
        # Получаем имена (попытка)
        try:
            m1 = await bot.get_chat_member(callback.message.chat.id, p1_id)
            m2 = await bot.get_chat_member(callback.message.chat.id, p2_id)
            n1 = f"@{m1.user.username}" if m1.user.username else m1.user.first_name
            n2 = f"@{m2.user.username}" if m2.user.username else m2.user.first_name
        except:
            n1, n2 = "Игрок 1", "Игрок 2"

        ACTIVE_DUELS[game_id] = {
            "p1": {"id": p1_id, "name": n1, "hp": 100, "class": None, "weapon": None, "ace_streak": 0, "buff_dmg": 0, "buff_heal": False, "buff_def": 0},
            "p2": {"id": p2_id, "name": n2, "hp": 100, "class": None, "weapon": None, "ace_streak": 0, "buff_dmg": 0, "buff_heal": False, "buff_def": 0},
            "state": "choosing_class", "log": "Ожидание выбора...", "lock": asyncio.Lock()
        }
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐍 Хантер", callback_data="pick_class_hunter"), InlineKeyboardButton(text="🔮 Варлок", callback_data="pick_class_warlock"), InlineKeyboardButton(text="🛡 Титан", callback_data="pick_class_titan")],
            [InlineKeyboardButton(text="♠️ Ace", callback_data="pick_weapon_ace"), InlineKeyboardButton(text="🤠 Last Word", callback_data="pick_weapon_lw")],
            [InlineKeyboardButton(text="🎲 Рандом", callback_data="pick_full_random")]
        ])
        await callback.message.edit_text(f"🎒 <b>ВЫБОР СНАРЯЖЕНИЯ</b>\n{n1} vs {n2}", reply_markup=kb)
        return

    # Если игры нет в ACTIVE_DUELS после всех проверок
    if game_id not in ACTIVE_DUELS:
        await callback.answer("Игра не найдена.", show_alert=True); return
        
    game = ACTIVE_DUELS[game_id]
    
    if action == "duel_refresh":
        await update_duel_message(callback, game_id)
        await callback.answer("Обновлено")
        return

    # --- БЛОКИРОВКА (LOCK) ДЛЯ АТОМАРНОСТИ ХОДА ---
    async with game["lock"]:
        if game.get("state") != "fighting":
            await callback.answer("Не все готовы!", show_alert=True); return

        shooter_id = callback.from_user.id
        if shooter_id != game["turn"]:
            await callback.answer("Не твой ход!", show_alert=True); return

        # Определяем кто есть кто
        if shooter_id == game["p1"]["id"]:
            shooter, target = game["p1"], game["p2"]
        else:
            shooter, target = game["p2"], game["p1"]

        # --- ОБРАБОТКА БАФФОВ ---
        if action in ["duel_buff_radiant", "duel_buff_devour", "duel_buff_amplify"]:
            buff_name, log_msg = "", ""
            
            if action == "duel_buff_radiant" and shooter["class"] == "hunter":
                shooter["buff_dmg"] = 10; buff_name = "Сияние"
                log_msg = f"{shooter['name']} активирует <b>Сияние</b>! (+10 урона)"
            elif action == "duel_buff_devour" and shooter["class"] == "warlock":
                shooter["buff_heal"] = True; buff_name = "Пожирание"
                log_msg = f"{shooter['name']} активирует <b>Пожирание</b>! (Хил при попадании)"
            elif action == "duel_buff_amplify" and shooter["class"] == "titan":
                shooter["buff_def"] = 10; buff_name = "Усиление"
                log_msg = f"{shooter['name']} получает <b>Усиление</b>! (Щит 10)"
            else:
                await callback.answer("Не твой класс!", show_alert=True); return

            # Обработка летящего Титана
            if game.get("pending_crash"):
                game["crash_turns"] -= 1
                if game["crash_turns"] <= 0:
                    titan_id = game["pending_crash"]
                    titan = game["p1"] if game["p1"]["id"] == titan_id else game["p2"]
                    enemy = game["p1"] if game["p1"]["id"] != titan_id else game["p2"]
                    game["pending_crash"] = None
                    
                    if random.randint(1, 100) <= 17:
                        # Титан попал после баффа врага
                        update_duel_stats(titan['id'], True); update_duel_stats(enemy['id'], False)
                        del ACTIVE_DUELS[game_id]
                        await callback.message.edit_text(f"🏆 <b>ПОБЕДА!</b>\n\n{log_msg}\n⚡ <b>БАБАХ!</b> {titan['name']} приземляется! (-100 HP)", reply_markup=None)
                        return
                    else:
                        log_msg += f"\n💨 {titan['name']} промахивается ультой!"
                        game["turn"] = titan_id
                else:
                    log_msg += "\n⏳ Титан летит! Остался 1 ход!"
                    game["turn"] = shooter["id"] # Ход сохраняется за баффером, если титан еще летит
            else:
                game["turn"] = target["id"]

            game["log"] = log_msg
            save_duels(ACTIVE_DUELS)
            await update_duel_message(callback, game_id)
            await callback.answer(f"{buff_name}!")
            return

        # --- ОБРАБОТКА ВЫСТРЕЛОВ ---
        if action in ["duel_shoot_primary", "duel_gg", "duel_nova", "duel_crash"]:
            if game.get("pending_crash") and action == "duel_crash":
                await callback.answer("Уже летишь!", show_alert=True); return
                
            # Проверка соответствия классу
            cls = shooter["class"]
            if (cls == "hunter" and action in ["duel_nova", "duel_crash"]) or \
               (cls == "warlock" and action in ["duel_gg", "duel_crash"]) or \
               (cls == "titan" and action in ["duel_gg", "duel_nova"]):
                await callback.answer("Не твоя абилка!", show_alert=True); return

            damage = 0
            log_msg = ""
            
            # 1. Основное оружие
            if action == "duel_shoot_primary":
                w_type = shooter["weapon"]
                if w_type == "ace":
                    update_usage(shooter_id, "w_ace")
                    streak = shooter.get("ace_streak", 0)
                    crit_chance = 10 if streak == 1 else 0
                    roll = random.randint(1, 100)
                    if roll <= crit_chance:
                        damage = 50; shooter["ace_streak"] = 0
                        log_msg = f"💀 <b>MEMENTO MORI!</b> {shooter['name']} критует Тузом! (50)"
                    elif roll <= (crit_chance + 50):
                        damage = 25; shooter["ace_streak"] = 1
                        log_msg = f"💥 <b>Попадание!</b> {shooter['name']} стреляет с Туза. (25)"
                    else:
                        damage = 0; shooter["ace_streak"] = 0
                        log_msg = f"💨 <b>Промах!</b> {shooter['name']} мажет с Туза."
                
                elif w_type == "lw":
                    update_usage(shooter_id, "w_lw")
                    shooter["ace_streak"] = 0
                    hits = 0
                    vis = ""
                    for _ in range(8):
                        if random.randint(1, 100) <= 34:
                            damage += 5; hits += 1; vis += "💥"
                        else: vis += " "
                    
                    if damage > 0: log_msg = f"🤠 <b>Fan Fire!</b> {hits} попаданий. ({damage})\n[{vis}]"
                    else: log_msg = f"🤠 <b>Промах!</b> Весь барабан мимо.\n[{vis}]"

            # 2. Ульта
            else:
                shooter["ace_streak"] = 0
                if action == "duel_gg":
                    update_usage(shooter_id, "w_gg")
                    if random.randint(1, 100) <= 9: damage = 100; log_msg = "💥 <b>КРИТ!</b> 🔥Golden Gun! (100)"
                    else: log_msg = "💨 GG пролетел мимо!"
                
                elif action == "duel_nova":
                    update_usage(shooter_id, "w_nova")
                    roll = random.randint(1, 100)
                    if roll <= 5: damage = 100; log_msg = "💥 <b>КРИТ!</b> НОВА! (100)"
                    elif roll <= 14: damage = 75; log_msg = "🟣 <b>Взрыв!</b> Нова задела краем. (75)"
                    else: log_msg = "💨 Нова улетела в стену."
                
                elif action == "duel_crash":
                    update_usage(shooter_id, "w_crash")
                    game["pending_crash"] = shooter_id
                    game["crash_turns"] = 2
                    game["turn"] = target["id"]
                    game["log"] = f"⚡ <b>ГРОМ!</b> {shooter['name']} взлетает! У врага 2 хода!"
                    save_duels(ACTIVE_DUELS)
                    await update_duel_message(callback, game_id)
                    await callback.answer()
                    return

            # --- ПРИМЕНЕНИЕ УРОНА И ЭФФЕКТОВ ---
            
            # Сияние (урон)
            if damage > 0 and shooter["buff_dmg"] > 0:
                damage += shooter["buff_dmg"]
                shooter["buff_dmg"] = 0
                log_msg += " (+10 Сияние)"

            # Усиление (щит цели)
            if damage > 0 and damage < 100 and target["buff_def"] > 0:
                blocked = min(damage, target["buff_def"])
                damage -= blocked
                target["buff_def"] -= blocked
                log_msg += f" (🛡 -{blocked})"

            # Пожирание (хил стрелка)
            if damage > 0 and shooter["buff_heal"] and action == "duel_shoot_primary":
                shooter["hp"] = min(100, shooter["hp"] + 10)
                shooter["buff_heal"] = False
                log_msg += " (🌀 +10 HP)"

            # Нанесение урона
            if damage > 0:
                target["hp"] -= damage
                if target["hp"] < 0: target["hp"] = 0

            # --- ПРОВЕРКА СМЕРТИ ---
            if target["hp"] <= 0:
                update_duel_stats(shooter['id'], True)
                update_duel_stats(target['id'], False)
                del ACTIVE_DUELS[game_id]
                save_duels(ACTIVE_DUELS)
                await callback.message.edit_text(f"🏆 <b>ПОБЕДА!</b>\n\n{log_msg}\n\n💀 {target['name']} повержен.", reply_markup=None)
                await callback.answer()
                return

            # --- ОБРАБОТКА ЛЕТЯЩЕГО ТИТАНА (Если защитник стрелял, пока титан летит) ---
            if game.get("pending_crash"):
                titan_id = game["pending_crash"]
                if shooter_id != titan_id: 
                    game["crash_turns"] -= 1
                    if game["crash_turns"] <= 0:
                        # Титан приземляется
                        titan = game["p1"] if game["p1"]["id"] == titan_id else game["p2"]
                        enemy = game["p1"] if game["p1"]["id"] != titan_id else game["p2"]
                        game["pending_crash"] = None
                        
                        if random.randint(1, 100) <= 17:
                            enemy["hp"] = 0
                            update_duel_stats(titan['id'], True); update_duel_stats(enemy['id'], False)
                            del ACTIVE_DUELS[game_id]
                            save_duels(ACTIVE_DUELS)
                            await callback.message.edit_text(f"🏆 <b>ПОБЕДА!</b>\n\n{log_msg}\n⚡ <b>БУУУМ!</b> {titan['name']} убил соперника ультой!", reply_markup=None)
                            return
                        else:
                            game["log"] = f"{log_msg}\n💨 {titan['name']} промахивается!"
                            game["turn"] = titan_id # Ход переходит к приземлившемуся титану
                    else:
                        game["log"] = f"{log_msg}\n⏳ Титан летит! 1 выстрел остался!"
                        game["turn"] = shooter_id # Ход остается у стрелка
            else:
                # Обычная смена хода
                game["turn"] = target["id"]
                game["log"] = log_msg

            save_duels(ACTIVE_DUELS)
            await update_duel_message(callback, game_id)
            await callback.answer()
            
