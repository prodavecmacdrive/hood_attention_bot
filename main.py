from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, PHONE, BOT_TOKEN, CHANNELS, KEYWORDS, TARGET_CHANNEL
from database import Database
from wizard import get_user_state, set_user_state, clear_user_state, get_wizard_data
from ml_matcher import get_matcher, MessageMatcher
from admin_help import optimize_all_districts
import logging

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Створення клієнтів
user_client = TelegramClient('bot_session', API_ID, API_HASH)  # User-акаунт для парсингу
bot_client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)  # Бот для керування

db = Database()

# ML модель (ледаче ініціалізація при першому використанні)
matcher = None

# ID адміністратора (ваш ID в Telegram)
ADMIN_ID = None  # Буде встановлено при запуску

# Тимчасове сховище для текстів повідомлень (для кнопок feedback)
# Ключ: (user_id, msg_id), Значення: текст повідомлення
message_cache = {}


# === МЕНЮ З КНОПКАМИ ===

def get_main_menu():
    """Головне меню з постійними кнопками"""
    return [
        [Button.text("📺 Канали", resize=True), Button.text("🔑 Слова", resize=True)],
        [Button.text("🤖 ML Приклади", resize=True), Button.text("🔄 Режим", resize=True)],
        [Button.text("📊 Статус", resize=True), Button.text("❓ Допомога", resize=True)]
    ]


# === КОМАНДИ ===

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Команда /start з головним меню"""
    user_id = event.sender_id
    district_id, setup_completed = db.get_user_settings(user_id)
    
    if not setup_completed:
        await event.respond(
            "👋 **Вітаємо!**\n\n"
            "Налаштуймо бота для моніторингу каналів.\n\n"
            "Використовуйте /setup для покрокового налаштування"
        )
    else:
        await event.respond(
            "🤖 **Бот для моніторингу Telegram каналів**\n\n"
            "Використовуйте кнопки меню нижче ⬇️",
            buttons=get_main_menu()
        )


@bot_client.on(events.NewMessage(pattern='/setup'))
async def setup_handler(event):
    """Начать пошаговую настройку"""
    user_id = event.sender_id
    
    # Получаем предустановленные каналы
    preset_channels = db.get_preset_channels()
    
    # По умолчанию выбираем ВСЕ каналы
    selected_channels = [username for username, name, desc in preset_channels]
    
    # Сохраняем начальное состояние с выбранными каналуми
    set_user_state(user_id, 'select_channels', {'selected_channels': selected_channels})
    
    buttons = []
    for username, name, desc in preset_channels:
        # Все каналы отмечены по умолчанию
        buttons.append([Button.inline(f"✅ {name}", f"channel_{username}")])
    
    buttons.append([Button.inline("➡️ Далее", "channels_done")])
    
    await event.respond(
        "**Шаг 1/3: Выбор каналів**\n\n"
        f"Выбрано каналів: {len(selected_channels)}\n\n"
        "Выберите каналы для мониторинга:\n"
        "(нажмите на канал чтобы додати/видалити)",
        buttons=buttons
    )


# === ОБРАБОТЧИКИ INLINE КНОПОК SETUP ===

@bot_client.on(events.CallbackQuery(pattern=b'channel_(.+)'))
async def channel_select_callback(event):
    """Выбор/отмена выбора каналу"""
    try:
        # Подтверждаем получение callback
        try:
            await event.answer()
        except:
            pass  # Игнорируем ошибки подтверждения
        
        channel = event.data.decode().replace('channel_', '')
        user_id = event.sender_id
        
        state = get_user_state(user_id)
        if state.get('step') != 'select_channels':
            return
        
        # Получаем текущие выбранные каналы
        selected = state.get('selected_channels', [])
        
        if channel in selected:
            selected.remove(channel)
        else:
            selected.append(channel)
        
        set_user_state(user_id, 'select_channels', {'selected_channels': selected})
        
        # Обновляем кнопки
        preset_channels = db.get_preset_channels()
        buttons = []
        
        for username, name, desc in preset_channels:
            prefix = "✅" if username in selected else "⬜"
            buttons.append([Button.inline(f"{prefix} {name}", f"channel_{username}")])
        
        buttons.append([Button.inline("➡️ Далее", "channels_done")])
        
        await event.edit(
            f"**Шаг 1/3: Выбор каналів**\n\n"
            f"Выбрано каналів: {len(selected)}\n\n"
            f"Выберите каналы для мониторинга:",
            buttons=buttons
        )
    except Exception as e:
        logger.error(f"Помилка в channel_select_callback: {e}")


@bot_client.on(events.CallbackQuery(pattern=b'channels_done'))
async def channels_done_callback(event):
    """Завершение выбора каналів"""
    try:
        # Подтверждаем получение callback
        try:
            await event.answer()
        except:
            pass
        
        user_id = event.sender_id
        state = get_user_state(user_id)
        
        selected_channels = state.get('selected_channels', [])
        
        if not selected_channels:
            await event.answer("Выберите хотя бы один канал!", alert=True)
            return
        
        # НЕ сохраняем каналы здесь, только переходим дальше
        # Каналы сохраним в конце настройки
        
        # Переход к выбору района - теперь ТЕКСТОВЫЙ ВВОД
        set_user_state(user_id, 'input_district', {'selected_channels': selected_channels})
        
        await event.edit(
            "**Шаг 2/3: Выбор района**\n\n"
            "📍 Введите название вашего района Харькова.\n\n"
            "Наприклад: `Салтовка`, `Павлово Поле`, `ХТЗ`\n\n"
            "Начните вводить, и я покажу подходящие варианты.",
            buttons=None
        )
    except Exception as e:
        logger.error(f"Помилка в channels_done_callback: {e}")


# Обработчик ввода района
@bot_client.on(events.NewMessage(func=lambda e: e.is_private and not e.forward and e.text and not e.text.startswith('/')))
async def text_input_handler(event):
    """Обработчик текстового ввода для поиска района с нечетким поиском"""
    user_id = event.sender_id
    state = get_user_state(user_id)
    
    # Проверяем, что пользователь в режиме ввода района
    if state.get('step') != 'input_district':
        return
    
    text = event.message.text.strip()
    
    logger.info(f"Поиск района по запросу: '{text}' для пользователя {user_id}")
    
    try:
        # Ищем районы с нечетким поиском (порог 60%)
        found_districts = db.search_districts(text, limit=10, threshold=60)
        
        logger.info(f"Найдено районов: {len(found_districts)}")
        
        if not found_districts:
            await event.respond(
                f"🔍 По запросу `{text}` ничего не найдено.\n\n"
                "💡 **Советы:**\n"
                "• Проверьте правописание\n"
                "• Попробуйте ввести часть названия (наприклад: `салт`, `хтз`, `павлов`)\n"
                "• Используйте команду /cancel для отмены\n\n"
                "📝 Примеры: `Салтовка`, `ХТЗ`, `Павлово Поле`, `602`",
                buttons=[[Button.inline("❌ Отмена", "setup_cancel")]]
            )
            return
        
        # Показываем найденные районы кнопками
        buttons = []
        
        # Отображаем процент совпадения для результатов < 100%
        for dist_id, dist_name, score in found_districts:
            if score >= 95:
                # Почти точное совпадение - не показываем процент
                button_text = f"📍 {dist_name}"
            else:
                # Показываем процент для нечетких совпадений
                button_text = f"📍 {dist_name} ({score}%)"
            
            buttons.append([Button.inline(button_text, f"district_{dist_id}")])
        
        # Добавляем кнопку отмены
        buttons.append([Button.inline("❌ Отмена", "setup_cancel")])
        
        # Формируем сообщение
        response_text = f"🔍 Найдено районов: **{len(found_districts)}**\n\n"
        
        # Выделяем лучшее совпадение
        if found_districts[0][2] >= 90:
            best_match = found_districts[0][1]
            response_text += f"✅ **Возможно вы ищете:** {best_match}\n\n"
        
        response_text += "Выберите ваш район:"
        
        await event.respond(
            response_text,
            buttons=buttons
        )
    except Exception as e:
        logger.error(f"Помилка поиска района: {e}", exc_info=True)
        await event.respond(
            f"❌ Помилка поиска: {e}",
            buttons=[[Button.inline("❌ Отмена", "setup_cancel")]]
        )


@bot_client.on(events.CallbackQuery(pattern=b'district_(\\d+)'))
async def district_select_callback(event):
    """Выбор района"""
    try:
        # Подтверждаем получение callback
        try:
            await event.answer()
        except:
            pass
        
        district_id = int(event.data.decode().replace('district_', ''))
        user_id = event.sender_id
        
        state = get_user_state(user_id)
        selected_channels = state.get('selected_channels', [])
        
        # Сохраняем выбранный район
        db.set_user_district(user_id, district_id)
        set_user_state(user_id, 'select_keywords', {
            'district_id': district_id,
            'selected_channels': selected_channels
        })
        
        # Получаем популярные слова для района
        popular_keywords = db.get_popular_keywords_for_district(district_id, limit=10)
        
        buttons = []
        
        if popular_keywords:
            for keyword, count in popular_keywords:
                buttons.append([Button.inline(f"✅ {keyword} ({count})", f"kw_{keyword}")])
            
            buttons.append([Button.inline("📝 Свои слова", "custom_keywords")])
        else:
            await event.answer("Пока нет популярных слов для этого района")
        
        buttons.append([Button.inline("✔️ Завершить", "setup_done")])
        
        # Получаем название района
        district_name = db.get_district_by_id(district_id)
        
        await event.edit(
            f"**Шаг 3/3: Ключевые слова**\n\n"
            f"📍 Район: **{district_name}**\n\n"
            f"Выберите популярные слова или добавьте свои:",
            buttons=buttons
        )
    except Exception as e:
        logger.error(f"Помилка в district_select_callback: {e}")


@bot_client.on(events.CallbackQuery(pattern=b'kw_(.+)'))
async def keyword_select_callback(event):
    """Выбор ключового слова"""
    try:
        # Подтверждаем получение callback
        try:
            await event.answer()
        except:
            pass
        
        keyword = event.data.decode().replace('kw_', '')
        user_id = event.sender_id
        
        state = get_user_state(user_id)
        selected_kw = state.get('selected_keywords', [])
        
        if keyword in selected_kw:
            selected_kw.remove(keyword)
        else:
            selected_kw.append(keyword)
        
        # Сохраняем все данные из state
        set_user_state(user_id, state['step'], {
            'selected_keywords': selected_kw, 
            'district_id': state.get('district_id'),
            'selected_channels': state.get('selected_channels', [])
        })
        
        await event.answer(f"{'Добавлено' if keyword in selected_kw else 'Удалено'}: {keyword}")
    except Exception as e:
        logger.error(f"Помилка в keyword_select_callback: {e}")


@bot_client.on(events.CallbackQuery(pattern=b'custom_keywords'))
async def custom_keywords_callback(event):
    """Добавление своих ключових слів"""
    try:
        await event.answer("Отправьте ключевые слова через запятую", alert=True)
        user_id = event.sender_id
        set_user_state(user_id, 'input_keywords', get_user_state(user_id))
    except Exception as e:
        logger.error(f"Помилка в custom_keywords_callback: {e}")


@bot_client.on(events.CallbackQuery(pattern=b'setup_done'))
async def setup_done_callback(event):
    """Завершение настройки"""
    try:
        # Подтверждаем получение callback
        try:
            await event.answer()
        except:
            pass
        
        user_id = event.sender_id
        state = get_user_state(user_id)
        
        selected_keywords = state.get('selected_keywords', [])
        district_id = state.get('district_id')
        selected_channels = state.get('selected_channels', [])
        
        # ТЕПЕРЬ сохраняем каналы (в конце настройки)
        for channel in selected_channels:
            try:
                db.add_channel(channel)
            except Exception as e:
                logger.error(f"Помилка доданоия каналу {channel}: {e}")
        
        # Сохраняем ключевые слова В ТАБЛИЦУ user_keywords (для этого пользователя)
        for keyword in selected_keywords:
            try:
                # Добавляем в общую таблицу keywords
                db.add_keyword(keyword)
                # Добавляем в user_keywords для этого пользователя
                db.add_user_keyword(user_id, keyword)
                # Увеличиваем популярность для района
                if district_id:
                    db.add_district_keyword(district_id, keyword)
            except Exception as e:
                logger.error(f"Помилка доданоия ключового слова {keyword}: {e}")
        
        # Завершаем настройку
        db.complete_user_setup(user_id)
        clear_user_state(user_id)
        
        await event.edit(
            "✅ **Настройка завершена!**\n\n"
            f"📺 Выбрано каналів: {len(db.get_channels())}\n"
            f"🔑 Ключевых слов: {len(selected_keywords)}\n\n"
            "Бот начал мониторинг! Используйте /start",
            buttons=None
        )
    except Exception as e:
        logger.error(f"Помилка в setup_done_callback: {e}")


# === ОБРАБОТЧИКИ КНОПОК МЕНЮ ===

@bot_client.on(events.NewMessage(pattern='📺 Каналы'))
async def channels_menu_handler(event):
    """Меню каналів"""
    channels = db.get_channels()
    if channels:
        channel_list = '\n'.join([f"• `{ch}`" for ch in channels])
        msg = f"📺 **Каналы ({len(channels)}):**\n\n{channel_list}\n\n"
    else:
        msg = "📺 **Каналы:**\n\nСписок пуст.\n\n"
    
    msg += "**Команды:**\n`/add_channel @username`\n`/remove_channel @username`"
    await event.respond(msg, buttons=get_main_menu())


@bot_client.on(events.NewMessage(pattern='🔑 Слова'))
async def keywords_menu_handler(event):
    """Меню ключових слів"""
    user_id = event.sender_id
    
    # Получаем ПЕРСОНАЛЬНЫЕ ключевые слова пользователя
    keywords = db.get_user_keywords(user_id)
    
    if keywords:
        keyword_list = '\n'.join([f"• `{kw}`" for kw in keywords])
        msg = f"🔑 **Ваши ключевые слова ({len(keywords)}):**\n\n{keyword_list}\n\n"
    else:
        msg = "🔑 **Ваши ключевые слова:**\n\nСписок пуст.\n\n"
    
    msg += "**Команды:**\n`/add_keyword слово`\n`/remove_keyword слово`"
    await event.respond(msg, buttons=get_main_menu())


@bot_client.on(events.NewMessage(pattern='🤖 ML Примеры'))
async def ml_examples_menu_handler(event):
    """Меню ML прикладів"""
    user_id = event.sender_id
    examples_count = db.get_user_examples_count(user_id)
    
    if examples_count > 0:
        msg = (
            f"🤖 **ML Примеры ({examples_count}):**\n\n"
            f"У вас сохранено **{examples_count}** прикладів сообщений.\n\n"
            f"Бот автоматически находит похожие сообщения в каналух используя искусственный интеллект.\n\n"
        )
    else:
        msg = (
            "🤖 **ML Примеры:**\n\n"
            "У вас поки немає прикладів.\n\n"
            "**Как это работает:**\n"
            "1. Перешлите боту сообщения, которые вас интересуют\n"
            "2. Бот запомнит их и будет искать похожие\n"
            "3. Когда в каналух появится похожее сообщение - вы получите уведомление\n\n"
        )
    
    msg += (
        "**Команды:**\n"
        "• Переслать сообщение боту - додати приклад\n"
        "`/clear_examples` - очистить все приклады\n"
        "`/examples_status` - показать статус ML\n\n"
        "💡 ML работает вместе с ключевыми словами"
    )
    
    await event.respond(msg, buttons=get_main_menu())


@bot_client.on(events.NewMessage(pattern='⚙️ Настройки'))
async def settings_menu_handler(event):
    """Меню настроек"""
    target = db.get_target_channel()
    await event.respond(
        f"⚙️ **Настройки:**\n\n"
        f"🎯 Целевой канал: `{target}`\n\n"
        f"**Команды:**\n`/set_target @channel`\n`/set_target me`",
        buttons=get_main_menu()
    )


@bot_client.on(events.NewMessage(pattern='📊 Статус'))
async def status_menu_handler(event):
    """Статус бота"""
    channels_count, keywords_count = db.get_stats()
    target = db.get_target_channel()
    
    await event.respond(
        f"📊 **Статус бота:**\n\n"
        f"📺 Каналов: **{channels_count}**\n"
        f"🔑 Ключевых слов: **{keywords_count}**\n"
        f"🎯 Целевой канал: `{target}`\n\n"
        f"✅ Бот работает и мониторит каналы",
        buttons=get_main_menu()
    )


@bot_client.on(events.NewMessage(pattern='🔄 Режим'))
async def mode_menu_handler(event):
    """Меню выбора режима работы"""
    user_id = event.sender_id
    current_mode = db.get_user_mode(user_id)
    district_id, setup_completed = db.get_user_settings(user_id)
    
    if not setup_completed:
        await event.respond(
            "⚠️ Сначала завершите настройку через /setup",
            buttons=get_main_menu()
        )
        return
    
    district_name = db.get_district_name(district_id)
    
    # Статистика
    personal_keywords = len(db.get_user_keywords(user_id))
    personal_examples = len(db.get_user_examples(user_id))
    
    optimized_keywords = len(db.get_optimized_keywords(district_id))
    optimized_examples = db.get_optimized_examples_count(district_id)
    district_users = db.get_district_users_count(district_id)
    
    mode_emoji = "✅" if current_mode == "personal" else "⬜"
    opt_emoji = "✅" if current_mode == "optimized" else "⬜"
    
    buttons = [
        [Button.inline(
            f"{mode_emoji} Персональный режим",
            "mode_personal"
        )],
        [Button.inline(
            f"{opt_emoji} Оптимізований режим",
            "mode_optimized"
        )],
        [Button.inline("🔙 Назад", "main_menu")]
    ]
    
    await event.respond(
        f"🔄 **Режим работы**\n\n"
        f"📍 Ваш район: **{district_name}**\n"
        f"👤 Поточний режим: **{current_mode}**\n\n"
        f"**Персональный режим:**\n"
        f"🔑 Ключевых слов: {personal_keywords}\n"
        f"🤖 ML прикладів: {personal_examples}\n\n"
        f"**Оптимізований режим:**\n"
        f"👥 Основан на данных {district_users} пользователей\n"
        f"🔑 Ключевых слов: {optimized_keywords}\n"
        f"🤖 ML прикладів: {optimized_examples}\n\n"
        f"💡 Выберите режим:",
        buttons=buttons
    )


@bot_client.on(events.CallbackQuery(pattern=b'mode_personal'))
async def mode_personal_callback(event):
    """Переключение на персональный режим"""
    try:
        await event.answer()
        user_id = event.sender_id
        
        db.set_user_mode(user_id, 'personal')
        
        await event.edit(
            "✅ **Персональный режим включен!**\n\n"
            "Используются только ваши ключевые слова и ML приклады.\n\n"
            "Используйте кнопку 🔄 Режим для изменения."
        )
        logger.info(f"Пользователь {user_id} переключился на personal режим")
    except Exception as e:
        logger.error(f"Помилка переключения режима: {e}")


@bot_client.on(events.CallbackQuery(pattern=b'mode_optimized'))
async def mode_optimized_callback(event):
    """Переключение на оптимизированный режим"""
    try:
        await event.answer()
        user_id = event.sender_id
        district_id, _ = db.get_user_settings(user_id)
        
        # Проверяем наличие оптимизированных данных
        opt_keywords = len(db.get_optimized_keywords(district_id))
        opt_examples = db.get_optimized_examples_count(district_id)
        
        if opt_keywords == 0 and opt_examples == 0:
            await event.answer(
                "⚠️ Для вашего района еще нет оптимизированных данных. "
                "Администратор должен запустить /admin_optimize",
                alert=True
            )
            return
        
        db.set_user_mode(user_id, 'optimized')
        
        await event.edit(
            f"✅ **Оптимізований режим включен!**\n\n"
            f"🔑 Используется {opt_keywords} ключових слів\n"
            f"🤖 Используется {opt_examples} ML прикладів\n\n"
            f"Данные основаны на коллективном опыте пользователей вашего района.\n\n"
            f"Используйте кнопку 🔄 Режим для изменения."
        )
        logger.info(f"Пользователь {user_id} переключился на optimized режим")
    except Exception as e:
        logger.error(f"Помилка переключения режима: {e}")


@bot_client.on(events.CallbackQuery(pattern=b'main_menu'))
async def main_menu_callback(event):
    """Возврат в главное меню"""
    try:
        await event.answer()
        await event.delete()
        await event.respond(
            "🤖 **Главное меню**",
            buttons=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Помилка возврата в меню: {e}")


# === ОБРАТНАЯ СВЯЗЬ (FEEDBACK) ===

@bot_client.on(events.CallbackQuery(pattern=rb'feedback_like_(\d+)'))
async def feedback_like_handler(event):
    """Обработчик позитивной обратной связи (👍)"""
    try:
        user_id = event.sender_id
        msg_id = int(event.pattern_match.group(1).decode())
        
        # Удаляем кнопки после нажатия
        await event.edit(buttons=None)
        await event.answer("✅ Дякуємо за відгук!")
        
        # Очищаем кэш
        message_cache.pop((user_id, msg_id), None)
        
        logger.info(f"Пользователь {user_id} поставил 👍 сообщению {msg_id}")
        
    except Exception as e:
        logger.error(f"Помилка обработки like: {e}")


@bot_client.on(events.CallbackQuery(pattern=rb'feedback_dislike_(\d+)'))
async def feedback_dislike_handler(event):
    """Обработчик негативной обратной связи (👎) - сохраняет как негативный приклад"""
    global matcher
    
    try:
        user_id = event.sender_id
        msg_id = int(event.pattern_match.group(1).decode())
        
        # Получаем текст сообщения из кэша
        cache_key = (user_id, msg_id)
        message_text = message_cache.get(cache_key)
        
        if not message_text:
            await event.answer("❌ Повідомлення не знайдено в кэше")
            return
        
        # Инициализируем matcher если нужно
        if matcher is None:
            matcher = get_matcher()
        
        # Создаем embedding для негативного приклада
        try:
            embedding = matcher.encode_text(message_text)
            embedding_bytes = MessageMatcher.serialize_embedding(embedding)
            
            # Сохраняем в БД как негативный приклад
            if db.add_negative_example(user_id, message_text, embedding_bytes):
                await event.answer("👎 Сохранено как негативный приклад")
                await event.edit(buttons=None)
                logger.info(f"Пользователь {user_id} добавил негативный приклад: '{message_text[:50]}...'")
            else:
                await event.answer("❌ Помилка сохранения")
                
        except Exception as e:
            logger.error(f"Помилка создания embedding для негативного приклада: {e}")
            await event.answer("❌ Помилка обработки")
        
        # Очищаем кэш
        message_cache.pop(cache_key, None)
        
    except Exception as e:
        logger.error(f"Помилка обработки dislike: {e}")
        await event.answer("❌ Произошла помилка")


@bot_client.on(events.NewMessage(pattern='❓ Допомога'))
async def help_menu_handler(event):
    """Довідка"""
    await event.respond(
        "📖 **Довідка:**\n\n"
        "**Керування каналуми:**\n"
        "`/add_channel @durov` - додати\n"
        "`/remove_channel @durov` - видалити\n\n"
        "**Ключові слова:**\n"
        "`/add_keyword біткоїн` - одне слово\n"
        "`/add_keyword біткоїн,місяць` - група (AND)\n"
        "`/remove_keyword біткоїн` - видалити\n\n"
        "**ML приклади:**\n"
        "`/clear_examples` - видалити всі приклади\n"
        "`/examples_status` - статистика\n\n"
        "**Зворотний зв'язок:**\n"
        "👍👎 - оцінюйте повідомлення\n"
        "`/dislikes_stats` - статистика дизлайків\n"
        "`/clear_dislikes` - очистити дизлайки\n\n"
        "**Режими роботи:**\n"
        "🔄 Режим - перемикання між режимами\n"
        "• Особистий - ваші дані\n"
        "• Оптимізований - дані району\n\n"
        "💡 Групи слів через кому шукають ВСІ слова разом",
        buttons=get_main_menu()
    )


# === КОМАНДЫ УПРАВЛЕНИЯ КАНАЛАМИ ===

@bot_client.on(events.NewMessage(pattern=r'/add_channel\s+(.+)'))
async def add_channel_text(event):
    """Добавить канал через команду"""
    channel = event.pattern_match.group(1).strip()
    
    if db.add_channel(channel):
        await event.respond(
            f"✅ Канал `{channel}` додано!",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            f"❌ Канал `{channel}` уже у списку",
            buttons=get_main_menu()
        )


@bot_client.on(events.NewMessage(pattern=r'/remove_channel\s+(.+)'))
async def remove_channel_text(event):
    """Удалить канал через команду"""
    channel = event.pattern_match.group(1).strip()
    
    if db.remove_channel(channel):
        await event.respond(
            f"✅ Канал `{channel}` видалено",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            f"❌ Канал `{channel}` не найден",
            buttons=get_main_menu()
        )


# === КОМАНДЫ УПРАВЛЕНИЯ КЛЮЧЕВЫМИ СЛОВАМИ ===

@bot_client.on(events.NewMessage(pattern=r'/add_keyword\s+(.+)'))
async def add_keyword_text(event):
    """Добавить ключевое слово для пользователя"""
    keyword = event.pattern_match.group(1).strip().lower()
    user_id = event.sender_id
    
    if db.add_user_keyword(user_id, keyword):
        # Также добавляем в общую таблицу и увеличиваем популярность
        db.add_keyword(keyword)
        district_id, _ = db.get_user_settings(user_id)
        if district_id:
            db.add_district_keyword(district_id, keyword)
        
        await event.respond(
            f"✅ Слово `{keyword}` доданоо в ваш список!",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            f"❌ Слово `{keyword}` уже в вашому списку",
            buttons=get_main_menu()
        )


# === ML ПРИМЕРЫ ===

@bot_client.on(events.NewMessage(func=lambda e: e.is_private and e.forward))
async def forwarded_message_handler(event):
    """Обработка пересланных сообщений - доданоие прикладів для ML"""
    global matcher
    
    user_id = event.sender_id
    
    # Проверяем, что пользователь завершил setup
    _, setup_completed = db.get_user_settings(user_id)
    if not setup_completed:
        await event.respond(
            "⚠️ Сначала завершите настройку через /setup",
            buttons=get_main_menu()
        )
        return
    
    # Получаем текст пересланного сообщения
    text = event.message.text
    if not text or len(text.strip()) < 10:
        await event.respond(
            "⚠️ Сообщение слишком короткое. Перешлите сообщение с текстом минимум 10 символов.",
            buttons=get_main_menu()
        )
        return
    
    try:
        # Инициализируем matcher при первом использовании
        global matcher
        if matcher is None:
            await event.respond("🔄 Загрузка ML модели... (первый запуск)")
            matcher = get_matcher()
        
        # Создаем embedding
        embedding = matcher.encode_text(text)
        embedding_bytes = MessageMatcher.serialize_embedding(embedding)
        
        # Сохраняем в БД
        if db.add_user_example(user_id, text, embedding_bytes):
            count = db.get_user_examples_count(user_id)
            await event.respond(
                f"✅ **Пример додано!**\n\n"
                f"Всього прикладів: **{count}**\n\n"
                f"💡 Бот будет искать похожие сообщения в каналух",
                buttons=get_main_menu()
            )
        else:
            await event.respond(
                "❌ Помилка сохранения приклада",
                buttons=get_main_menu()
            )
    except Exception as e:
        logger.error(f"Помилка обработки приклада: {e}")
        await event.respond(
            f"❌ Помилка: {e}",
            buttons=get_main_menu()
        )


@bot_client.on(events.NewMessage(pattern='/clear_examples'))
async def clear_examples_handler(event):
    """Очистить все приклады пользователя"""
    user_id = event.sender_id
    
    if db.clear_user_examples(user_id):
        await event.respond(
            "✅ Все приклады видаленоы",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            "❌ Помилка видаленоия прикладів",
            buttons=get_main_menu()
        )


@bot_client.on(events.NewMessage(pattern='/dislikes_stats'))
async def dislikes_stats_handler(event):
    """Показать статистику негативных прикладів (дизлайків)"""
    user_id = event.sender_id
    
    count = db.get_negative_examples_count(user_id)
    negative_examples = db.get_negative_examples(user_id)
    
    response = f"👎 **Негативные приклады (дизлайки):**\n\n"
    response += f"Всього: **{count}**\n\n"
    
    if negative_examples:
        response += "📋 **Последние приклады:**\n"
        for text, _ in negative_examples[:5]:  # Показываем первые 5
            preview = text[:60] + "..." if len(text) > 60 else text
            response += f"• {preview}\n"
        
        if count > 5:
            response += f"\n_...и ещё {count - 5}_"
    else:
        response += "⚠️ У вас поки немає негативных прикладів\n\n"
        response += "💡 Натискайте 👎 на нерелевантних повідомленнях, щоб покращити фільтрацію"
    
    await event.respond(response, buttons=get_main_menu())


@bot_client.on(events.NewMessage(pattern='/clear_dislikes'))
async def clear_dislikes_handler(event):
    """Очистить все негативные приклады (дизлайки)"""
    user_id = event.sender_id
    
    if db.clear_negative_examples(user_id):
        await event.respond(
            "✅ Все негативные приклады видаленоы",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            "❌ Помилка видаленоия негативных прикладів",
            buttons=get_main_menu()
        )


@bot_client.on(events.NewMessage(pattern='/examples_status'))
async def examples_status_handler(event):
    """Показать статус ML"""
    global matcher
    user_id = event.sender_id
    
    count = db.get_user_examples_count(user_id)
    ml_status = "✅ Завантажена" if matcher is not None else "⏳ Не завантажена (загрузится при первом прикладе)"
    
    await event.respond(
        f"🤖 **Статус ML:**\n\n"
        f"ML модель: {ml_status}\n"
        f"Ваших прикладів: **{count}**\n\n"
        f"{'✅ ML активний и шукає схожі повідомлення' if count > 0 else '⚠️ Добавьте приклады, переславши повідомлення боту'}",
        buttons=get_main_menu()
    )


@bot_client.on(events.NewMessage(pattern=r'/remove_keyword\s+(.+)'))
async def remove_keyword_text(event):
    """Удалить ключевое слово пользователя"""
    keyword = event.pattern_match.group(1).strip().lower()
    user_id = event.sender_id
    
    if db.remove_user_keyword(user_id, keyword):
        await event.respond(
            f"✅ Слово `{keyword}` видаленоо из вашого списку",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            f"❌ Слово `{keyword}` не найдено в вашому списку",
            buttons=get_main_menu()
        )


# === НАСТРОЙКИ ===

@bot_client.on(events.NewMessage(pattern=r'/set_target\s+(.+)'))
async def set_target_text(event):
    """Установить целевой канал"""
    target = event.pattern_match.group(1).strip()
    
    if db.set_target_channel(target):
        await event.respond(
            f"✅ Целевой канал: `{target}`",
            buttons=get_main_menu()
        )
    else:
        await event.respond(
            "❌ Помилка установки",
            buttons=get_main_menu()
        )


# === ОБРАБОТЧИК СООБЩЕНИЙ ИЗ КАНАЛОВ (User-аккаунт) ===

@user_client.on(events.NewMessage())
async def message_handler(event):
    """Обработчик новых сообщений из отслеживаемых каналів"""
    # Пропускаем личные сообщения
    if event.is_private:
        return
    
    # Проверяем, что сообщение из отслеживаемого каналу
    channels = db.get_channels()
    chat_username = f"@{event.chat.username}" if event.chat.username else None
    
    if not chat_username or chat_username not in channels:
        return
    
    try:
        message_text = event.message.text
        
        if not message_text:
            return
            
        message_lower = message_text.lower()
        
        # Получаем всех активных пользователей
        active_users = db.get_all_active_users()
        
        if not active_users:
            logger.debug("Нет активных пользователей для отправки")
            return
        
        # Для каждого пользователя проверяем его настройки
        for user_id, district_id in active_users:
            try:
                # Получаем режим пользователя
                user_mode = db.get_user_mode(user_id)
                
                # В зависимости от режима берем разные данные
                if user_mode == 'optimized':
                    # Используем оптимизированные данные района
                    user_keywords = db.get_optimized_keywords(district_id)
                    user_examples = db.get_optimized_examples(district_id)
                else:  # personal
                    # Используем персональные данные пользователя
                    user_keywords = db.get_user_keywords(user_id)
                    user_examples = db.get_user_examples(user_id)
                
                # Проверка 1: Ключевые слова (быстрая)
                matched_keywords = False
                matched_keyword_list = []
                
                if user_keywords:
                    for keyword in user_keywords:
                        # Проверяем каждое слово пользователя
                        if keyword in message_lower:
                            matched_keywords = True
                            matched_keyword_list.append(keyword)
                
                # Проверка 2: ML сходство (если есть приклады)
                matched_ml = False
                ml_similarity = 0.0
                
                if user_examples and matcher is not None:
                    try:
                        # Десериализуем embeddings
                        example_embeddings = [
                            MessageMatcher.deserialize_embedding(emb_bytes) 
                            for _, emb_bytes in user_examples
                        ]
                        
                        # Проверяем сходство (порог 75%)
                        matched_ml = matcher.is_similar(
                            message_text, 
                            example_embeddings, 
                            threshold=0.75
                        )
                        
                        if matched_ml:
                            # Находим лучшее совпадение для логирования
                            text_embedding = matcher.encode_text(message_text)
                            for example_emb in example_embeddings:
                                sim = matcher.cosine_similarity(text_embedding, example_emb)
                                ml_similarity = max(ml_similarity, sim)
                    except Exception as e:
                        logger.error(f"Помилка ML проверки для пользователя {user_id}: {e}")
                
                # Проверка 3: Негативные приклады (фильтрация ложных срабатываний)
                blocked_by_negative = False
                max_negative_similarity = 0.0
                
                if (matched_keywords or matched_ml) and matcher is not None:
                    try:
                        # Получаем негативные приклады пользователя
                        negative_examples = db.get_negative_examples(user_id)
                        
                        if negative_examples:
                            # Десериализуем embeddings негативных прикладів
                            negative_embeddings = [
                                MessageMatcher.deserialize_embedding(emb_bytes)
                                for _, emb_bytes in negative_examples
                            ]
                            
                            # Создаем embedding текущего сообщения
                            text_embedding = matcher.encode_text(message_text)
                            
                            # Проверяем схожесть с негативными прикладами
                            for neg_emb in negative_embeddings:
                                sim = matcher.cosine_similarity(text_embedding, neg_emb)
                                max_negative_similarity = max(max_negative_similarity, sim)
                            
                            # Блокируем если слишком похоже на негативный приклад
                            if max_negative_similarity > 0.85:
                                blocked_by_negative = True
                                logger.info(
                                    f"Сообщение заблокировано негативным прикладом для пользователя {user_id} "
                                    f"(similarity: {max_negative_similarity:.2%})"
                                )
                            # Дополнительная проверка: если позитивное совпадение слабое, а негативное сильное
                            elif matched_ml and ml_similarity < 0.80 and max_negative_similarity > 0.70:
                                blocked_by_negative = True
                                logger.info(
                                    f"Сообщение заблокировано (слабое позитивное {ml_similarity:.2%}, "
                                    f"сильное негативное {max_negative_similarity:.2%})"
                                )
                                
                    except Exception as e:
                        logger.error(f"Помилка проверки негативных прикладів для пользователя {user_id}: {e}")
                
                # Если совпало ИЛИ по ключевым словам ИЛИ по ML - отправляем (если не заблокировано)
                if (matched_keywords or matched_ml) and not blocked_by_negative:
                    try:
                        # Создаем кнопки для обратной связи
                        msg_id = event.message.id
                        feedback_buttons = [
                            Button.inline("👍 Полезно", f"feedback_like_{msg_id}"),
                            Button.inline("👎 Не то", f"feedback_dislike_{msg_id}")
                        ]
                        
                        # Сохраняем текст сообщения в кэш для будущего использования в feedback
                        message_cache[(user_id, msg_id)] = message_text
                        
                        # Отправляем копию сообщения с кнопками
                        await bot_client.send_message(
                            user_id,
                            event.message.text or "",
                            buttons=feedback_buttons,
                            file=event.message.media if event.message.media else None
                        )
                        
                        match_reason = []
                        if matched_keywords:
                            match_reason.append(f"keywords: {matched_keyword_list[:3]}")  # Только первые 3
                        if matched_ml:
                            match_reason.append(f"ML: {ml_similarity:.2%}")
                        
                        mode_label = "optimized" if user_mode == 'optimized' else "personal"
                        
                        logger.info(
                            f"Сообщение переслано пользователю {user_id} "
                            f"[{mode_label}] ({', '.join(match_reason)})"
                        )
                    except Exception as e:
                        logger.error(f"Помилка отправки пользователю {user_id}: {e}")
                        
            except Exception as e:
                logger.error(f"Помилка обработки для пользователя {user_id}: {e}")
            
    except Exception as e:
        logger.error(f"Помилка обработки сообщения: {e}")


# === АДМИН-КОМАНДЫ ===

@bot_client.on(events.NewMessage(pattern='/admin_optimize'))
async def admin_optimize_handler(event):
    """Оптимизация данных для всех районов (только для админа)"""
    user_id = event.sender_id
    
    if user_id != ADMIN_ID:
        await event.respond("⛔ Эта команда доступна только администратору")
        return
    
    await event.respond("⏳ **Начинаю оптимизацию...**\n\nЭто может занять несколько минут...")
    
    try:
        # Запускаем оптимизацию
        results = optimize_all_districts(db)
        
        if not results:
            await event.respond("❌ Нет районов с пользователями для оптимизации")
            return
        
        # Формируем отчет
        response = "✅ **Оптимизация завершена!**\n\n"
        response += f"Обработано районов: {len(results)}\n\n"
        
        for district_id, district_name, users_count, keywords_count, examples_count in results:
            response += (
                f"📍 **{district_name}**\n"
                f"   👥 Пользователей: {users_count}\n"
                f"   🔑 Ключевых слов: {keywords_count}\n"
                f"   🤖 ML прикладів: {examples_count}\n\n"
            )
        
        await event.respond(response)
        logger.info(f"Админ {user_id} выполнил оптимизацию")
        
    except Exception as e:
        logger.error(f"Помилка оптимизации: {e}", exc_info=True)
        await event.respond(f"❌ Помилка при оптимизации: {e}")


@bot_client.on(events.NewMessage(pattern='/admin_stats'))
async def admin_stats_handler(event):
    """Статистика по районам (только для админа)"""
    user_id = event.sender_id
    
    if user_id != ADMIN_ID:
        await event.respond("⛔ Эта команда доступна только администратору")
        return
    
    try:
        stats = db.get_optimization_stats()
        
        if not stats:
            await event.respond("📊 Пока нет данных для статистики")
            return
        
        response = "📊 **Статистика по районам:**\n\n"
        
        # Показываем только районы с пользователями
        active_stats = [(name, users, kw, ex) for name, users, kw, ex in stats if users > 0]
        
        if not active_stats:
            await event.respond("📊 Нет активных районов с пользователями")
            return
        
        total_users = sum(users for _, users, _, _ in active_stats)
        total_keywords = sum(kw for _, _, kw, _ in active_stats)
        total_examples = sum(ex for _, _, _, ex in active_stats)
        
        response += f"**Общая статистика:**\n"
        response += f"👥 Всього пользователей: {total_users}\n"
        response += f"🗺️ Активных районов: {len(active_stats)}\n"
        response += f"🔑 Уникальных слов: {total_keywords}\n"
        response += f"🤖 ML прикладів: {total_examples}\n\n"
        
        response += "**Топ-10 районов:**\n\n"
        
        for i, (district_name, users_count, keywords_count, examples_count) in enumerate(active_stats[:10], 1):
            response += (
                f"{i}. **{district_name}**\n"
                f"   👥 {users_count} польз. | 🔑 {keywords_count} слов | 🤖 {examples_count} прим.\n\n"
            )
        
        await event.respond(response)
        logger.info(f"Админ {user_id} запросил статистику")
        
    except Exception as e:
        logger.error(f"Помилка получения статистики: {e}", exc_info=True)
        await event.respond(f"❌ Помилка: {e}")


# === ЗАПУСК БОТА ===

async def main():
    """Запуск бота"""
    global ADMIN_ID
    
    logger.info("Запуск бота...")
    
    # Проверка конфигурации
    if not API_ID or not API_HASH or not PHONE:
        logger.error("Помилка: не заданы API_ID, API_HASH или PHONE в файле .env")
        return
    
    if not BOT_TOKEN:
        logger.error("Помилка: не задан BOT_TOKEN в файле .env")
        return
    
    # Запускаем user-аккаунт для парсинга
    await user_client.start(phone=PHONE)
    
    # Получаем ID администратора (вас)
    me = await user_client.get_me()
    ADMIN_ID = me.id
    logger.info(f"User-аккаунт авторизован: {me.first_name} (ID: {ADMIN_ID})")
    
    # Инициализация БД из .env при первом запуске
    if not db.get_channels() and CHANNELS:
        logger.info("Импорт начальных каналів из .env...")
        for channel in CHANNELS:
            db.add_channel(channel)
    
    if not db.get_keywords() and KEYWORDS:
        logger.info("Импорт начальных ключових слів из .env...")
        for keyword in KEYWORDS:
            db.add_keyword(keyword)
    
    if TARGET_CHANNEL:
        db.set_target_channel(TARGET_CHANNEL)
    
    # Получаем текущие настройки из БД
    channels = db.get_channels()
    keywords = db.get_keywords()
    target = db.get_target_channel()
    
    if not channels:
        logger.warning("⚠️ Нет каналів для мониторинга. Добавьте каналы через /add_channel")
    
    if not keywords:
        logger.warning("⚠️ Нет ключових слів. Добавьте слова через /add_keyword")
    
    # Получаем информацию о боте
    bot_me = await bot_client.get_me()
    logger.info(f"Бот для управления запущен: @{bot_me.username}")
    
    logger.info("=" * 50)
    logger.info("Бот успешно запущен!")
    logger.info(f"📺 Отслеживаемые каналы ({len(channels)}): {channels}")
    logger.info(f"🔑 Ключевые слова ({len(keywords)}): {keywords}")
    logger.info(f"🎯 Целевой канал: {target}")
    logger.info(f"🤖 Управление: напишите /start боту @{bot_me.username}")
    logger.info("=" * 50)
    
    # Запускаем обоих клиентов
    await user_client.run_until_disconnected()


if __name__ == '__main__':
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
