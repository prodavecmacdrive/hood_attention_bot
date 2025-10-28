# Состояния wizard'а для настройки
WIZARD_STATES = {}

def get_user_state(user_id):
    """Получить текущее состояние пользователя"""
    return WIZARD_STATES.get(user_id, {'step': None})

def set_user_state(user_id, step, data=None):
    """Установить состояние пользователя"""
    if user_id not in WIZARD_STATES:
        WIZARD_STATES[user_id] = {}
    WIZARD_STATES[user_id]['step'] = step
    if data:
        WIZARD_STATES[user_id].update(data)

def clear_user_state(user_id):
    """Очистить состояние пользователя"""
    if user_id in WIZARD_STATES:
        del WIZARD_STATES[user_id]

def get_wizard_data(user_id, key):
    """Получить данные из состояния"""
    return WIZARD_STATES.get(user_id, {}).get(key)
