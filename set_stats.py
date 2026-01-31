import sqlite3
import os

# Пути (как в боте)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")

# ID пользователя
TARGET_ID = 832840031 

# --- ТВОИ ДАННЫЕ (МЕНЯЙ ТУТ) ---
WINS = 15
LOSSES = 3
POINTS = 350

# Классы (сколько раз играл)
CLASS_HUNTER = 10
CLASS_WARLOCK = 5
CLASS_TITAN = 3

# Оружие (сколько раз стрелял)
W_ACE = 20
W_LW = 5
W_GG = 2
W_NOVA = 1
W_CRASH = 0

print(f"📂 Подключаемся к базе: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Проверяем колонки (на всякий случай)
try:
    cursor.execute("ALTER TABLE users ADD COLUMN class_hunter INTEGER DEFAULT 0")
except: pass # Уже есть

# Записываем данные
try:
    # 1. Создаем или обновляем запись
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (TARGET_ID,))
    
    # 2. Обновляем все поля
    cursor.execute('''
        UPDATE users SET 
            wins = ?, losses = ?, points = ?,
            class_hunter = ?, class_warlock = ?, class_titan = ?,
            w_ace = ?, w_lw = ?, w_gg = ?, w_nova = ?, w_crash = ?
        WHERE user_id = ?
    ''', (
        WINS, LOSSES, POINTS,
        CLASS_HUNTER, CLASS_WARLOCK, CLASS_TITAN,
        W_ACE, W_LW, W_GG, W_NOVA, W_CRASH,
        TARGET_ID
    ))
    
    conn.commit()
    print(f"✅ УСПЕХ! Статистика для {TARGET_ID} обновлена.")
    print(f"🏆 Побед: {WINS} | Рейтинг: {POINTS}")
    print(f"🔫 Любимое оружие обновлено.")

except Exception as e:
    print(f"❌ Ошибка записи: {e}")

conn.close()
