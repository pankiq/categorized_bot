from datetime import datetime

# Глобальные переменные состояния
PENDING_VERIFICATION = {}
PROCESSED_ALBUMS = []
LAST_MESSAGE_TIME = datetime.now()
AI_COOLDOWN_TIME = datetime.now()
SUMMARY_COOLDOWN_TIME = datetime.now()

# Турнир
TOURNAMENT_ACTIVE = False
TOURNAMENT_MAX_PLAYERS = 0
TOURNAMENT_PLAYERS = []
TOURNAMENT_USERNAMES = []

# Чат и Лор
CHAT_HISTORY = []
SILENT_MODE_USERS = []
USED_LORE_FACTS = []

# Игры
ACTIVE_DUELS = {} # Загрузим в database.py или games.py
