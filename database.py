import sqlite3
import os
import json
import asyncio
from config import DB_PATH, DUELS_FILE

# Подключение к БД
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")
conn.commit()

# Создание таблицы
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    )
''')
conn.commit()

# Миграция колонок
new_columns = [
    "class_hunter", "class_warlock", "class_titan",
    "w_ace", "w_lw", "w_gg", "w_nova", "w_crash"
]
for col in new_columns:
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
    except Exception:
        pass 
conn.commit()

# --- ФУНКЦИИ ---
def load_duels():
    """Загружает игры и восстанавливает asyncio.Lock"""
    if os.path.exists(DUELS_FILE):
        try:
            with open(DUELS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                duels = {}
                for k, v in data.items():
                    game_id = int(k)
                    v["lock"] = asyncio.Lock() 
                    duels[game_id] = v
                return duels
        except Exception as e:
            print(f"Ошибка загрузки дуэлей: {e}")
            return {}
    return {}

def save_duels(active_duels_dict):
    """Сохраняет игры в файл"""
    try:
        data_to_save = {}
        for k, v in active_duels_dict.items():
            game_copy = v.copy()
            if "lock" in game_copy: del game_copy["lock"]
            if "last_update" in game_copy: del game_copy["last_update"]
            data_to_save[k] = game_copy
            
        with open(DUELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения дуэлей: {e}")

def get_user_data(user_id):
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row: return dict(row)
        else: return {'wins': 0, 'losses': 0, 'points': 0}
    except Exception as e:
        print(f"Ошибка БД (get): {e}") 
        return {'wins': 0, 'losses': 0, 'points': 0}

def update_usage(user_id, field):
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        cursor.execute(f'UPDATE users SET {field} = {field} + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Ошибка обновления статы использования: {e}")

def update_duel_stats(user_id, is_winner):
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        if is_winner:
            cursor.execute('UPDATE users SET wins = wins + 1, points = points + 25 WHERE user_id = ?', (user_id,))
        else:
            cursor.execute('UPDATE users SET losses = losses + 1, points = MAX(0, points - 10) WHERE user_id = ?', (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Ошибка БД (stats): {e}")
