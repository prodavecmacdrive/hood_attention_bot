import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API (получить на https://my.telegram.org/apps)
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE = os.getenv('PHONE', '+380000000000')

# Bot Token для управления (получить у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Каналы для мониторинга (разделенные запятыми)
CHANNELS = [ch.strip() for ch in os.getenv('CHANNELS', '@example_channel1,@example_channel2').split(',') if ch.strip()]

# Ключевые слова для поиска (разделенные запятыми)
KEYWORDS = [kw.strip() for kw in os.getenv('KEYWORDS', 'keyword1,keyword2').split(',') if kw.strip()]

# Целевой канал для репоста (обычно 'me' для Избранного)
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', 'me')
