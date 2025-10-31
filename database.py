import sqlite3
import logging
from typing import List, Tuple
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path='bot_config.db'):
        self.db_path = db_path
        self.init_db()
    
    def _get_connection(self):
        """Получить соединение с таймаутом"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging для лучшей параллельности
        return conn
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблица для каналов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Таблица для ключевых слов (группы слов через запятую = AND)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword_group TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Таблица для настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Таблица предустановленных каналов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preset_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT UNIQUE NOT NULL,
                channel_name TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # Таблица районов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS districts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_name TEXT UNIQUE NOT NULL,
                area_name TEXT NOT NULL
            )
        ''')
        
        # Таблица микрорайонов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subdistricts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_id INTEGER NOT NULL,
                subdistrict_name TEXT NOT NULL,
                FOREIGN KEY (district_id) REFERENCES districts(id)
            )
        ''')
        
        # Таблица популярных ключевых слов по районам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS district_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                usage_count INTEGER DEFAULT 1,
                FOREIGN KEY (district_id) REFERENCES districts(id),
                UNIQUE(district_id, keyword)
            )
        ''')
        
        # Таблица пользовательских настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                selected_district_id INTEGER,
                setup_completed INTEGER DEFAULT 0,
                mode TEXT DEFAULT 'personal',
                FOREIGN KEY (selected_district_id) REFERENCES districts(id)
            )
        ''')
        
        # Таблица ключевых слов пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user_settings(user_id),
                UNIQUE(user_id, keyword)
            )
        ''')
        
        # Таблица примеров сообщений для ML
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                example_text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
            )
        ''')
        
        # Таблица негативных примеров (дизлайки)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_negative_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                example_text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
            )
        ''')

        # Таблица для хранения истории сообщений из каналов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                message_text TEXT,
                message_date TIMESTAMP NOT NULL,
                embedding BLOB,
                UNIQUE(channel_username, message_id)
            )
        ''')
        
        # Таблица оптимизированных ключевых слов по районам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS district_optimized_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                weight REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (district_id) REFERENCES districts(id),
                UNIQUE(district_id, keyword)
            )
        ''')
        
        # Таблица оптимизированных ML примеров по районам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS district_optimized_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_id INTEGER NOT NULL,
                example_text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                cluster_id INTEGER,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (district_id) REFERENCES districts(id)
            )
        ''')
        
        # Таблица логов оптимизации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS district_optimization_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_id INTEGER NOT NULL,
                users_count INTEGER DEFAULT 0,
                keywords_count INTEGER DEFAULT 0,
                examples_count INTEGER DEFAULT 0,
                optimized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (district_id) REFERENCES districts(id)
            )
        ''')
        
        conn.commit()
        
        # Заполняем предустановленные данные при первом запуске
        self._populate_preset_data(cursor, conn)
        
        conn.close()
        logger.info("База данных инициализирована")
    
    def _populate_preset_data(self, cursor, conn):
        """Заполнение предустановленных каналов и районов"""
        # Проверяем, есть ли уже данные
        cursor.execute('SELECT COUNT(*) FROM preset_channels')
        if cursor.fetchone()[0] > 0:
            return  # Данные уже есть
        
        # Предустановленные каналы
        preset_channels = [
            ('@monitor1654', 'Monitor 1654', 'Мониторинг Харьков'),
            ('@kpszsu', 'КПСЗ ЗСУ', 'Командование ПС ЗСУ'),
            ('@radar_kharkov', 'Radar Kharkiv', 'Радар Харьков'),
            ('@war_monitor', 'War Monitor', 'Мониторинг войны'),
            ('@tlknewsua', 'TLK News UA', 'Новости Украины')
        ]
        
        cursor.executemany(
            'INSERT OR IGNORE INTO preset_channels (channel_username, channel_name, description) VALUES (?, ?, ?)',
            preset_channels
        )
        
        # Районы Харькова (плоский список)
        districts = [
            'Салтовка', 'Северная Салтовка', 'Восточная Салтовка', 'Шишковка', 
            'Тюринка', 'Журавлёвка', 'Большая Даниловка', 'Малая Даниловка', 
            'Пятихатки', 'посёлок Жуковского', 'Нагорный район (центр)', 
            'Павлово Поле', 'Алексеевка', 'Шатиловка', 'Сосновая Горка', 
            '602-й микрорайон', 'Аэропорт', 'Одесская', 'Новые Дома', 
            'Коммунальный рынок', 'Немышля', 'Восточный', 
            'ХТЗ (Харьковский тракторный завод)', 'Рогань', 'Горизонт', 
            'Солнечный', 'Хролы', 'Залютино', 'Холодная Гора', 'Лысая Гора', 
            'Ивановка', 'Гиёвка', 'Новая Бавария', 'Бавария', 'Октябрьское', 
            'Филипповка', 'Григоровка', 'Основа', 'Левада', 'Качановка', 
            'Москалёвка', 'Подол', 'Заиковка', 'Жихарь', 
            'Селекционная станция', 'Померки', 'Сортировка', 'Диканевка', 
            'Благовещенский базар', 'Конный рынок', 'Кулиничи', 
            'Большая Рогань', 'Городской', 'Куряж', 'Пересечное', 
            'Солоницевка', 'Песочин', 'Безлюдовка', 'Васищево', 
            'Покотиловка', 'Мерефа'
        ]
        
        for district in districts:
            cursor.execute(
                'INSERT OR IGNORE INTO districts (district_name, area_name) VALUES (?, ?)',
                (district, 'Харьков')
            )
        
        conn.commit()
        logger.info("Предустановленные данные добавлены")
    
    # === КАНАЛЫ ===
    
    def add_channel(self, channel: str) -> bool:
        """Добавить канал для мониторинга"""
        try:
            # Убираем @ если есть
            channel = channel.strip()
            if not channel.startswith('@'):
                channel = '@' + channel
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Используем INSERT OR IGNORE вместо обычного INSERT
            cursor.execute('INSERT OR IGNORE INTO channels (channel_username) VALUES (?)', (channel,))
            
            # Проверяем, была ли вставка
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"Канал {channel} добавлен")
                return True
            else:
                conn.close()
                logger.debug(f"Канал {channel} уже существует")
                return True  # Возвращаем True, т.к. канал есть в базе
        except sqlite3.OperationalError as e:
            if 'locked' in str(e):
                logger.warning(f"База данных заблокирована при добавлении канала {channel}, повторная попытка...")
                import time
                time.sleep(0.1)
                return self.add_channel(channel)  # Retry
            else:
                logger.error(f"Ошибка добавления канала: {e}")
                return False
        except Exception as e:
            logger.error(f"Ошибка добавления канала: {e}")
            return False
    
    def remove_channel(self, channel: str) -> bool:
        """Удалить канал из мониторинга"""
        try:
            channel = channel.strip()
            if not channel.startswith('@'):
                channel = '@' + channel
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM channels WHERE channel_username = ?', (channel,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if deleted:
                logger.info(f"Канал {channel} удален")
            else:
                logger.warning(f"Канал {channel} не найден")
            return deleted
        except Exception as e:
            logger.error(f"Ошибка удаления канала: {e}")
            return False
    
    def get_channels(self) -> List[str]:
        """Получить список всех каналов"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT channel_username FROM channels')
            channels = [row[0] for row in cursor.fetchall()]
            conn.close()
            return channels
        except Exception as e:
            logger.error(f"Ошибка получения каналов: {e}")
            return []
    
    # === КЛЮЧЕВЫЕ СЛОВА (ГРУППЫ) ===
    
    def add_keyword(self, keyword: str) -> bool:
        """Добавить ключевое слово или группу слов (через запятую = AND)"""
        try:
            # Нормализуем: убираем лишние пробелы, приводим к нижнему регистру
            keyword = ','.join([w.strip().lower() for w in keyword.split(',') if w.strip()])
            
            if not keyword:
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Используем INSERT OR IGNORE
            cursor.execute('INSERT OR IGNORE INTO keywords (keyword_group) VALUES (?)', (keyword,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"Ключевая группа '{keyword}' добавлена")
                return True
            else:
                conn.close()
                logger.debug(f"Ключевая группа '{keyword}' уже существует")
                return True  # Возвращаем True, т.к. слово есть в базе
        except sqlite3.OperationalError as e:
            if 'locked' in str(e):
                logger.warning(f"База данных заблокирована при добавлении ключевого слова {keyword}, повторная попытка...")
                import time
                time.sleep(0.1)
                return self.add_keyword(keyword)  # Retry
            else:
                logger.error(f"Ошибка добавления ключевой группы: {e}")
                return False
        except Exception as e:
            logger.error(f"Ошибка добавления ключевой группы: {e}")
            return False
    
    def remove_keyword(self, keyword: str) -> bool:
        """Удалить ключевое слово или группу"""
        try:
            # Нормализуем так же как при добавлении
            keyword = ','.join([w.strip().lower() for w in keyword.split(',') if w.strip()])
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM keywords WHERE keyword_group = ?', (keyword,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if deleted:
                logger.info(f"Ключевая группа '{keyword}' удалена")
            else:
                logger.warning(f"Ключевая группа '{keyword}' не найдена")
            return deleted
        except Exception as e:
            logger.error(f"Ошибка удаления ключевой группы: {e}")
            return False
    
    def get_keywords(self) -> List[str]:
        """Получить список всех ключевых групп"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT keyword_group FROM keywords')
            keywords = [row[0] for row in cursor.fetchall()]
            conn.close()
            return keywords
        except Exception as e:
            logger.error(f"Ошибка получения ключевых слов: {e}")
            return []
    
    # === НАСТРОЙКИ ===
    
    def set_target_channel(self, channel: str) -> bool:
        """Установить целевой канал для репоста"""
        try:
            channel = channel.strip()
            if channel != 'me' and not channel.startswith('@'):
                channel = '@' + channel
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                ('target_channel', channel)
            )
            conn.commit()
            conn.close()
            logger.info(f"Целевой канал установлен: {channel}")
            return True
        except Exception as e:
            logger.error(f"Ошибка установки целевого канала: {e}")
            return False
    
    def get_target_channel(self) -> str:
        """Получить целевой канал"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', ('target_channel',))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 'me'
        except Exception as e:
            logger.error(f"Ошибка получения целевого канала: {e}")
            return 'me'
    
    def get_stats(self) -> Tuple[int, int]:
        """Получить статистику (кол-во каналов, кол-во ключевых слов)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM channels')
            channels_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM keywords')
            keywords_count = cursor.fetchone()[0]
            
            conn.close()
            return channels_count, keywords_count
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return 0, 0
    
    # === ПРЕДУСТАНОВЛЕННЫЕ КАНАЛЫ ===
    
    def get_preset_channels(self) -> List[Tuple[str, str, str]]:
        """Получить список предустановленных каналов"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT channel_username, channel_name, description FROM preset_channels')
            channels = cursor.fetchall()
            conn.close()
            return channels
        except Exception as e:
            logger.error(f"Ошибка получения предустановленных каналов: {e}")
            return []
    
    # === РАЙОНЫ ===
    
    def get_all_districts(self) -> List[Tuple[int, str]]:
        """Получить список всех районов"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, district_name FROM districts ORDER BY district_name')
            districts = cursor.fetchall()
            conn.close()
            return districts
        except Exception as e:
            logger.error(f"Ошибка получения районов: {e}")
            return []
    
    def search_districts(self, query: str, limit: int = 10, threshold: int = 60) -> List[Tuple[int, str, int]]:
        """
        Поиск районов с нечетким совпадением (fuzzy search)
        
        Args:
            query: Строка поиска (часть названия или с опечатками)
            limit: Максимальное количество результатов
            threshold: Минимальный процент совпадения (0-100), по умолчанию 60
            
        Returns:
            Список кортежей (id, district_name, score) отсортированный по релевантности
        """
        try:
            if not query or len(query) < 1:
                return []
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Получаем все районы
            cursor.execute('SELECT id, district_name FROM districts')
            all_districts = cursor.fetchall()
            conn.close()
            
            query_lower = query.lower().strip()
            
            # Используем rapidfuzz для нечеткого поиска
            results = []
            
            for dist_id, dist_name in all_districts:
                dist_name_lower = dist_name.lower()
                
                # Вычисляем разные типы совпадения:
                # 1. Частичное совпадение (partial_ratio) - для подстрок
                partial_score = fuzz.partial_ratio(query_lower, dist_name_lower)
                
                # 2. Соотношение токенов (token_sort_ratio) - игнорирует порядок слов
                token_score = fuzz.token_sort_ratio(query_lower, dist_name_lower)
                
                # 3. WRatio - взвешенное соотношение (универсальное)
                wratio_score = fuzz.WRatio(query_lower, dist_name_lower)
                
                # Берем максимальный скор
                max_score = max(partial_score, token_score, wratio_score)
                
                # Бонус +10% если запрос точно в начале названия
                if dist_name_lower.startswith(query_lower):
                    max_score = min(100, max_score + 10)
                
                # Бонус +5% если запрос содержится целиком в названии
                elif query_lower in dist_name_lower:
                    max_score = min(100, max_score + 5)
                
                if max_score >= threshold:
                    results.append((dist_id, dist_name, max_score))
            
            # Сортируем по убыванию релевантности (score), затем по имени
            results.sort(key=lambda x: (-x[2], x[1]))
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Ошибка поиска районов: {e}", exc_info=True)
            return []
    
    def get_district_by_id(self, district_id: int) -> str:
        """Получить название района по ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT district_name FROM districts WHERE id = ?', (district_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else ""
        except Exception as e:
            logger.error(f"Ошибка получения района: {e}")
            return ""
    
    def get_subdistricts(self, district_id: int) -> List[str]:
        """Получить микрорайоны для района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT subdistrict_name FROM subdistricts WHERE district_id = ?',
                (district_id,)
            )
            subdistricts = [row[0] for row in cursor.fetchall()]
            conn.close()
            return subdistricts
        except Exception as e:
            logger.error(f"Ошибка получения микрорайонов: {e}")
            return []
    
    # === ПОПУЛЯРНЫЕ КЛЮЧЕВЫЕ СЛОВА ПО РАЙОНАМ ===
    
    def get_popular_keywords_for_district(self, district_id: int, limit: int = 10) -> List[Tuple[str, int]]:
        """Получить популярные ключевые слова для района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT keyword, usage_count FROM district_keywords 
                   WHERE district_id = ? 
                   ORDER BY usage_count DESC LIMIT ?''',
                (district_id, limit)
            )
            keywords = cursor.fetchall()
            conn.close()
            return keywords
        except Exception as e:
            logger.error(f"Ошибка получения популярных слов: {e}")
            return []
    
    def get_keywords_for_district(self, district_id: int) -> List[str]:
        """Получить все активные ключевые слова (упрощенная версия - пока без фильтрации по району)"""
        try:
            # Пока возвращаем все ключевые слова, т.к. связь keywords<->district_keywords нужно переделать
            return self.get_keywords()
        except Exception as e:
            logger.error(f"Ошибка получения ключевых слов района: {e}")
            return []
    
    def add_district_keyword(self, district_id: int, keyword: str):
        """Добавить или увеличить счетчик ключевого слова для района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO district_keywords (district_id, keyword, usage_count) 
                   VALUES (?, ?, 1)
                   ON CONFLICT(district_id, keyword) DO UPDATE SET 
                   usage_count = usage_count + 1''',
                (district_id, keyword.lower())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка добавления ключевого слова района: {e}")
    
    # === ПОЛЬЗОВАТЕЛЬСКИЕ НАСТРОЙКИ ===
    
    def get_user_settings(self, user_id: int) -> Tuple[int, bool]:
        """Получить настройки пользователя (district_id, setup_completed)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT selected_district_id, setup_completed FROM user_settings WHERE user_id = ?',
                (user_id,)
            )
            result = cursor.fetchone()
            conn.close()
            if result:
                return result[0], bool(result[1])
            return None, False
        except Exception as e:
            logger.error(f"Ошибка получения настроек пользователя: {e}")
            return None, False
    
    def get_all_active_users(self) -> list:
        """Получить всех пользователей, завершивших настройку"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_id, selected_district_id FROM user_settings WHERE setup_completed = 1'
            )
            users = cursor.fetchall()
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Ошибка получения активных пользователей: {e}")
            return []
    
    def set_user_district(self, user_id: int, district_id: int):
        """Установить район пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO user_settings (user_id, selected_district_id, setup_completed) 
                   VALUES (?, ?, 0)
                   ON CONFLICT(user_id) DO UPDATE SET 
                   selected_district_id = ?, setup_completed = 0''',
                (user_id, district_id, district_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка установки района пользователя: {e}")
    
    def complete_user_setup(self, user_id: int):
        """Отметить настройку пользователя как завершенную"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO user_settings (user_id, setup_completed) 
                   VALUES (?, 1)
                   ON CONFLICT(user_id) DO UPDATE SET setup_completed = 1''',
                (user_id,)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка завершения настройки: {e}")
    
    # === КЛЮЧЕВЫЕ СЛОВА ПОЛЬЗОВАТЕЛЕЙ ===
    
    def add_user_keyword(self, user_id: int, keyword: str) -> bool:
        """Добавить ключевое слово для пользователя"""
        try:
            keyword = keyword.strip().lower()
            if not keyword:
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO user_keywords (user_id, keyword) VALUES (?, ?)',
                (user_id, keyword)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления ключевого слова пользователя: {e}")
            return False
    
    def remove_user_keyword(self, user_id: int, keyword: str) -> bool:
        """Удалить ключевое слово пользователя"""
        try:
            keyword = keyword.strip().lower()
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_keywords WHERE user_id = ? AND keyword = ?',
                (user_id, keyword)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления ключевого слова пользователя: {e}")
            return False
    
    def get_user_keywords(self, user_id: int) -> List[str]:
        """Получить все ключевые слова пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT keyword FROM user_keywords WHERE user_id = ?',
                (user_id,)
            )
            keywords = [row[0] for row in cursor.fetchall()]
            conn.close()
            return keywords
        except Exception as e:
            logger.error(f"Ошибка получения ключевых слов пользователя: {e}")
            return []
    
    # === ML ПРИМЕРЫ СООБЩЕНИЙ ===
    
    def add_user_example(self, user_id: int, text: str, embedding: bytes) -> bool:
        """Добавить пример сообщения для пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO user_examples (user_id, example_text, embedding) VALUES (?, ?, ?)',
                (user_id, text, embedding)
            )
            conn.commit()
            conn.close()
            logger.info(f"Добавлен пример для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления примера: {e}")
            return False
    
    def get_user_examples(self, user_id: int) -> List[Tuple[str, bytes]]:
        """Получить все примеры пользователя (текст, embedding)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT example_text, embedding FROM user_examples WHERE user_id = ?',
                (user_id,)
            )
            examples = cursor.fetchall()
            conn.close()
            return examples
        except Exception as e:
            logger.error(f"Ошибка получения примеров: {e}")
            return []
    
    # === РЕЖИМЫ РАБОТЫ ПОЛЬЗОВАТЕЛЯ ===
    
    def get_user_mode(self, user_id: int) -> str:
        """Получить режим работы пользователя (personal/optimized)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT mode FROM user_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 'personal'
        except Exception as e:
            logger.error(f"Ошибка получения режима пользователя: {e}")
            return 'personal'
    
    def set_user_mode(self, user_id: int, mode: str) -> bool:
        """Установить режим работы пользователя"""
        try:
            if mode not in ['personal', 'optimized']:
                logger.error(f"Неверный режим: {mode}")
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE user_settings SET mode = ? WHERE user_id = ?',
                (mode, user_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"Режим пользователя {user_id} изменен на {mode}")
            return True
        except Exception as e:
            logger.error(f"Ошибка установки режима: {e}")
            return False
    
    # === ОПТИМИЗИРОВАННЫЕ ДАННЫЕ ПО РАЙОНАМ ===
    
    def get_optimized_keywords(self, district_id: int) -> List[str]:
        """Получить оптимизированные ключевые слова для района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT keyword FROM district_optimized_keywords WHERE district_id = ? ORDER BY weight DESC',
                (district_id,)
            )
            keywords = [row[0] for row in cursor.fetchall()]
            conn.close()
            return keywords
        except Exception as e:
            logger.error(f"Ошибка получения оптимизированных ключевых слов: {e}")
            return []
    
    def get_optimized_examples(self, district_id: int) -> List[Tuple[str, bytes]]:
        """Получить оптимизированные ML примеры для района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT example_text, embedding FROM district_optimized_examples WHERE district_id = ? ORDER BY weight DESC',
                (district_id,)
            )
            examples = cursor.fetchall()
            conn.close()
            return examples
        except Exception as e:
            logger.error(f"Ошибка получения оптимизированных примеров: {e}")
            return []
    
    def get_optimized_examples_count(self, district_id: int) -> int:
        """Получить количество оптимизированных примеров"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM district_optimized_examples WHERE district_id = ?',
                (district_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка получения количества примеров: {e}")
            return 0
    
    def clear_optimized_keywords(self, district_id: int) -> bool:
        """Очистить оптимизированные ключевые слова района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM district_optimized_keywords WHERE district_id = ?',
                (district_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки оптимизированных ключевых слов: {e}")
            return False
    
    def clear_optimized_examples(self, district_id: int) -> bool:
        """Очистить оптимизированные ML примеры района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM district_optimized_examples WHERE district_id = ?',
                (district_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки оптимизированных примеров: {e}")
            return False
    
    def add_optimized_keyword(self, district_id: int, keyword: str, usage_count: int, weight: float) -> bool:
        """Добавить оптимизированное ключевое слово"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO district_optimized_keywords (district_id, keyword, usage_count, weight) VALUES (?, ?, ?, ?)',
                (district_id, keyword, usage_count, weight)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления оптимизированного ключевого слова: {e}")
            return False
    
    def add_optimized_example(self, district_id: int, text: str, embedding: bytes, cluster_id: int, weight: float) -> bool:
        """Добавить оптимизированный ML пример"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO district_optimized_examples (district_id, example_text, embedding, cluster_id, weight) VALUES (?, ?, ?, ?, ?)',
                (district_id, text, embedding, cluster_id, weight)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления оптимизированного примера: {e}")
            return False
    
    def get_district_users(self, district_id: int) -> List[int]:
        """Получить всех пользователей района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_id FROM user_settings WHERE selected_district_id = ? AND setup_completed = 1',
                (district_id,)
            )
            users = [row[0] for row in cursor.fetchall()]
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Ошибка получения пользователей района: {e}")
            return []
    
    def get_district_users_count(self, district_id: int) -> int:
        """Получить количество пользователей района"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM user_settings WHERE selected_district_id = ? AND setup_completed = 1',
                (district_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0
    
    def log_optimization(self, district_id: int, users_count: int, keywords_count: int, examples_count: int) -> bool:
        """Сохранить лог оптимизации"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO district_optimization_log (district_id, users_count, keywords_count, examples_count) VALUES (?, ?, ?, ?)',
                (district_id, users_count, keywords_count, examples_count)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения лога оптимизации: {e}")
            return False
    
    def get_optimization_stats(self) -> List[Tuple[str, int, int, int]]:
        """Получить статистику оптимизации по всем районам"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    d.district_name,
                    (SELECT COUNT(*) FROM user_settings WHERE selected_district_id = d.id AND setup_completed = 1) as users_count,
                    (SELECT COUNT(DISTINCT keyword) FROM user_keywords uk 
                     JOIN user_settings us ON uk.user_id = us.user_id 
                     WHERE us.selected_district_id = d.id) as keywords_count,
                    (SELECT COUNT(*) FROM user_examples ue 
                     JOIN user_settings us ON ue.user_id = us.user_id 
                     WHERE us.selected_district_id = d.id) as examples_count
                FROM districts d
                ORDER BY users_count DESC
            ''')
            stats = cursor.fetchall()
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики оптимизации: {e}")
            return []
    
    def get_district_name(self, district_id: int) -> str:
        """Получить название района по ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT district_name FROM districts WHERE id = ?', (district_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else "Неизвестный район"
        except Exception as e:
            logger.error(f"Ошибка получения названия района: {e}")
            return "Ошибка"
            return []
    
    def get_user_examples_count(self, user_id: int) -> int:
        """Получить количество примеров пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM user_examples WHERE user_id = ?',
                (user_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка подсчета примеров: {e}")
            return 0
    
    def remove_user_example(self, user_id: int, example_id: int) -> bool:
        """Удалить пример по ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_examples WHERE user_id = ? AND id = ?',
                (user_id, example_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления примера: {e}")
            return False
    
    def clear_user_examples(self, user_id: int) -> bool:
        """Очистить все примеры пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_examples WHERE user_id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
            logger.info(f"Очищены все примеры пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки примеров: {e}")
            return False
    
    # === НЕГАТИВНЫЕ ПРИМЕРЫ (ДИЗЛАЙКИ) ===
    
    def add_negative_example(self, user_id: int, text: str, embedding: bytes) -> bool:
        """Добавить негативный пример (дизлайк) для пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO user_negative_examples (user_id, example_text, embedding) VALUES (?, ?, ?)',
                (user_id, text, embedding)
            )
            conn.commit()
            conn.close()
            logger.info(f"Добавлен негативный пример для пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления негативного примера: {e}")
            return False
    
    def get_negative_examples(self, user_id: int) -> List[Tuple[str, bytes]]:
        """Получить все негативные примеры пользователя (текст, embedding)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT example_text, embedding FROM user_negative_examples WHERE user_id = ?',
                (user_id,)
            )
            examples = cursor.fetchall()
            conn.close()
            return examples
        except Exception as e:
            logger.error(f"Ошибка получения негативных примеров: {e}")
            return []
    
    def get_negative_examples_count(self, user_id: int) -> int:
        """Получить количество негативных примеров пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM user_negative_examples WHERE user_id = ?',
                (user_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка подсчета негативных примеров: {e}")
            return 0
    
    def clear_negative_examples(self, user_id: int) -> bool:
        """Очистить все негативные примеры пользователя"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_negative_examples WHERE user_id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
            logger.info(f"Очищены все негативные примеры пользователя {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки негативных примеров: {e}")
            return False

    # === ИСТОРИЯ СООБЩЕНИЙ ===

    def add_historical_message(self, channel_username: str, message_id: int, message_text: str, message_date, embedding: bytes = None):
        """Добавить сообщение из истории в базу данных"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR IGNORE INTO historical_messages 
                   (channel_username, message_id, message_text, message_date, embedding) 
                   VALUES (?, ?, ?, ?, ?)''',
                (channel_username, message_id, message_text, message_date, embedding)
            )
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка добавления исторического сообщения: {e}")
            return False

    def get_recent_historical_messages(self, minutes_ago: int = 30) -> List[Tuple]:
        """Получить недавние сообщения из всех каналов"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT channel_username, message_id, message_text, message_date, embedding 
                   FROM historical_messages 
                   WHERE message_date >= datetime('now', ?, 'localtime')
                   ORDER BY message_date DESC""",
                (f'-{minutes_ago} minutes',)
            )
            messages = cursor.fetchall()
            conn.close()
            return messages
        except Exception as e:
            logger.error(f"Ошибка получения недавних исторических сообщений: {e}")
            return []

    def get_latest_message_date(self, channel_username: str):
        """Получить дату последнего сохраненного сообщения для канала"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(message_date) FROM historical_messages WHERE channel_username = ?",
                (channel_username,)
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Ошибка получения даты последнего сообщения: {e}")
            return None

