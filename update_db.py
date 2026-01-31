import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "database.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

columns = [
    "class_hunter", "class_warlock", "class_titan",
    "w_ace", "w_lw", "w_gg", "w_nova", "w_crash"
]

print("Начинаю обновление базы...")

for col in columns:
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
        print(f"✅ Добавлена колонка: {col}")
    except sqlite3.OperationalError:
        print(f"ℹ️ Колонка {col} уже существует")
    except Exception as e:
        print(f"❌ Ошибка с {col}: {e}")

conn.commit()
conn.close()
print("Готово!")
