import os
from aiogram import Bot
from openai import AsyncOpenAI

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "key"  # Вставь свой токен сюда
OPENAI_API_KEY = "sk-keys" # Вставь ключ OpenAI

BOT_GUIDE = "https://telegra.ph/Baraholka-Bot-01-22"
LINK_TAPIR_GUIDE = "https://t.me/destinygoods/9814"
LINK_RULES = "https://telegra.ph/Pravila-kanala-i-chata-09-18"
LINK_CHAT = "https://t.me/+Uaa0ALuvIfs1MzYy"

OWNER_ID = 832840031
ADMIN_CHAT_ID = -1003376406623
CHAT_ID = -1002129048580
KEEP_POSTED_STICKER_ID = "CAACAgIAAxkBAAEQSpppcOtmxGDL9gH882Rg8pZrq5eXVAACXZAAAtfYYEiWmZcGWSTJ5TgE"
MORNING_VOICE_ID = "AwACAgIAAxkBAAOnaXymlPVFa4x2wuzZZ0nPOgyvDuIAAq-MAALP-uBL4TESKm_ZL344BA"

# Инициализация объектов, которые нужны везде
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.artemox.com/v1"
)

# Пути к БД
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")
DUELS_FILE = os.path.join(DATA_DIR, "duels.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
