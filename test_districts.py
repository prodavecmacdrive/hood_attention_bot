from database import Database
import logging
import sqlite3

# Включаем отладку
logging.basicConfig(level=logging.DEBUG)

db = Database()

# Добавляем тестовый район на латинице
print('=== Добавление тестовых районов ===')
conn = sqlite3.connect('bot_config.db')
cur = conn.cursor()

# Добавляем латинский район
cur.execute('INSERT OR IGNORE INTO districts (district_name, area_name) VALUES (?, ?)', ('Saltovka Test', 'Харьков'))
cur.execute('INSERT OR IGNORE INTO districts (district_name, area_name) VALUES (?, ?)', ('KhTZ Factory', 'Харьков'))
conn.commit()
conn.close()
print('Тестовые районы добавлены\n')

# Проверяем все районы
districts = db.get_all_districts()
print(f'Всего районов: {len(districts)}')
print('\nПоследние 5 (включая тестовые):')
for d in districts[-5:]:
    print(f'  {d[0]}: {d[1]}')

# Тестируем поиск
print('\n--- Тест поиска ---')
test_queries = [
    'салт',      # кириллица
    'хтз',       # кириллица
    'pavlov',    # латиница (если нет в БД)
    'salt',      # латиница (наш тест)
    'khtз',      # латиница (наш тест)
    '602',       # цифры
    'Saltovka',  # латиница с заглавной
]

for q in test_queries:
    print(f'\n=== Ищем "{q}" ===')
    results = db.search_districts(q)
    print(f'Найдено: {len(results)}')
    for d in results[:3]:
        print(f'  {d[0]}: {d[1]}')

# Дополнительная проверка - вручную проверяем кириллицу
print('\n--- Ручная проверка кириллицы ---')
all_districts = db.get_all_districts()
query = 'салт'
print(f'Ищем "{query}" вручную в Python:')
for dist_id, dist_name in all_districts:
    if query.lower() in dist_name.lower():
        print(f'  НАЙДЕНО: {dist_id}: {dist_name}')
