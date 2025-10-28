# coding: utf-8
import sqlite3

def search_districts_direct(query: str):
    """Прямой поиск без класса Database"""
    conn = sqlite3.connect('bot_config.db', timeout=10.0)
    cursor = conn.cursor()
    
    # Получаем все районы
    cursor.execute('SELECT id, district_name FROM districts')
    all_districts = cursor.fetchall()
    conn.close()
    
    print(f'\n=== Поиск "{query}" ===')
    print(f'Всего районов: {len(all_districts)}')
    print(f'query type: {type(query)}, repr: {repr(query)}')
    
    query_lower = query.lower()
    print(f'query_lower: {repr(query_lower)}')
    
    # Показываем несколько районов
    print('\nПервые 5 районов:')
    for dist_id, dist_name in all_districts[:5]:
        print(f'  {dist_id}: {repr(dist_name)}')
    
    # Ищем
    results = []
    for dist_id, dist_name in all_districts:
        dist_name_lower = dist_name.lower()
        
        # Показываем районы со "салт" или "salt"
        if 'салт' in dist_name_lower or 'salt' in dist_name_lower:
            print(f'\nКандидат: {repr(dist_name)}')
            print(f'  lower: {repr(dist_name_lower)}')
            print(f'  "{query_lower}" in "{dist_name_lower}": {query_lower in dist_name_lower}')
        
        if query_lower in dist_name_lower:
            results.append((dist_id, dist_name))
    
    print(f'\n  Результат: {len(results)} районов')
    for r in results:
        print(f'    {r}')
    
    return results


# Тест 1: кириллица
results1 = search_districts_direct('салт')

# Тест 2: латиница  
results2 = search_districts_direct('salt')

# Тест 3: цифры
results3 = search_districts_direct('602')
