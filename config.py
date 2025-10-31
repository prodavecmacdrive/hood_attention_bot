import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE = os.getenv('PHONE', '')

# Bot Token для управления
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Каналы для мониторинга (разделенные запятыми)
CHANNELS = [ch.strip() for ch in os.getenv('CHANNELS', '').split(',') if ch.strip()]

# Ключевые слова для поиска (разделенные запятыми)
KEYWORDS = [kw.strip() for kw in os.getenv('KEYWORDS', '').split(',') if kw.strip()]

# Целевой канал для репоста
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', '')
