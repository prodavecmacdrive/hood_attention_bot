# coding: utf-8
from database import Database
import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

db = Database()

print('=== Тест метода search_districts ===\n')

# Тест 1: кириллица
query1 = 'салт'
print(f'Запрос: "{query1}"')
print(f'repr: {repr(query1)}')
results1 = db.search_districts(query1)
print(f'Результат: {len(results1)} районов')
for r in results1:
    print(f'  {r}')

print('\n' + '='*50 + '\n')

# Тест 2: латиница
query2 = 'salt'
print(f'Запрос: "{query2}"')
print(f'repr: {repr(query2)}')
results2 = db.search_districts(query2)
print(f'Результат: {len(results2)} районов')
for r in results2:
    print(f'  {r}')
