# coding: utf-8
import sqlite3

# Открываем базу
conn = sqlite3.connect('bot_config.db')
cursor = conn.cursor()

# Получаем все районы
cursor.execute('SELECT id, district_name FROM districts')
all_districts = cursor.fetchall()
conn.close()

print(f'Всего районов: {len(all_districts)}')

# Тестируем поиск вручную
query = 'салт'
query_lower = query.lower()

print(f'\n=== Поиск "{query}" ===')
print(f'query_lower = {repr(query_lower)}')
print(f'Тип: {type(query_lower)}')

found = []
for dist_id, dist_name in all_districts:
    if 'салт' in dist_name.lower() or 'Салт' in dist_name:
        print(f'\nПроверяем: {dist_name}')
        print(f'  dist_name = {repr(dist_name)}')
        print(f'  dist_name.lower() = {repr(dist_name.lower())}')
        print(f'  query_lower in dist_name.lower() = {query_lower in dist_name.lower()}')
        
        if query_lower in dist_name.lower():
            found.append(dist_name)

print(f'\n=== Результат ===')
print(f'Найдено через "in": {len(found)}')
for f in found:
    print(f'  - {f}')

# Тест с латиницей
print(f'\n=== Поиск "salt" ===')
query2 = 'salt'
query2_lower = query2.lower()
found2 = []

for dist_id, dist_name in all_districts:
    if query2_lower in dist_name.lower():
        found2.append(dist_name)
        print(f'  НАЙДЕНО: {dist_name}')

print(f'Найдено: {len(found2)}')
