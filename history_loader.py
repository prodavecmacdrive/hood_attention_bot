"""
Модуль для загрузки историчесских сообщений из Telegram каналов.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from database import Database

logger = logging.getLogger(__name__)

class HistoryLoader:
    def __init__(self, client: TelegramClient, db: Database):
        self.client = client
        self.db = db

    async def load_history_for_all_channels(self, months_ago: int = 2):
        """
        Загружает историю сообщений для всех отслеживаемых каналов.
        
        Args:
            months_ago (int): Глубина загрузки в месяцах, если история для канала пуста.
        """
        channels = self.db.get_channels()
        if not channels:
            logger.warning("Нет каналов для загрузки истории.")
            return

        logger.info(f"Начинаю загрузку истории для {len(channels)} каналов...")
        
        tasks = [self.load_history_for_channel(channel, months_ago) for channel in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при загрузке истории для канала {channels[i]}: {result}")
            else:
                success_count += 1
                logger.info(f"Канал {channels[i]}: загружено {result} новых сообщений.")
        
        logger.info(f"Загрузка истории завершена. Успешно обработано {success_count}/{len(channels)} каналов.")

    async def load_history_for_channel(self, channel_username: str, months_ago: int = 2) -> int:
        """
        Загружает историю для одного канала, начиная с последнего сохраненного сообщения.
        """
        try:
            entity = await self.client.get_entity(channel_username)
        except Exception as e:
            logger.error(f"Не удалось получить доступ к каналу {channel_username}: {e}")
            return 0

        # Определяем, с какого момента загружать историю
        latest_date_str = self.db.get_latest_message_date(channel_username)
        offset_date = None
        if latest_date_str:
            # Загружаем с даты последнего сообщения
            offset_date = datetime.fromisoformat(latest_date_str)
            logger.info(f"Для канала {channel_username} найдена последняя запись: {offset_date}. Начинаю загрузку с этой даты.")
        else:
            # Загружаем за последние N месяцев
            offset_date = datetime.now() - timedelta(days=30 * months_ago)
            logger.info(f"Для канала {channel_username} история пуста. Загружаю за последние {months_ago} месяца (с {offset_date}).")

        message_count = 0
        try:
            async for message in self.client.iter_messages(entity, offset_date=offset_date, reverse=True):
                if not message.text:
                    continue

                # Сохраняем в БД
                added = self.db.add_historical_message(
                    channel_username=channel_username,
                    message_id=message.id,
                    message_text=message.text,
                    message_date=message.date
                )
                if added:
                    message_count += 1
                
                if message_count > 0 and message_count % 500 == 0:
                    logger.info(f"Промежуточный результат для {channel_username}: загружено {message_count} сообщений...")

        except Exception as e:
            logger.error(f"Произошла ошибка во время итерации по сообщениям канала {channel_username}: {e}", exc_info=True)
        
        return message_count
