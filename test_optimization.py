# coding: utf-8
"""
Тест системы оптимизации районов
"""
from database import Database
from admin_help import optimize_all_districts
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

print("="*60)
print("ТЕСТ СИСТЕМЫ ОПТИМИЗАЦИИ")
print("="*60)

# 1. Проверяем текущих пользователей
print("\n1. Текущие пользователи:")
stats = db.get_optimization_stats()
active_stats = [(name, users, kw, ex) for name, users, kw, ex in stats if users > 0]

if active_stats:
    for district_name, users_count, keywords_count, examples_count in active_stats:
        print(f"   📍 {district_name}: {users_count} польз., {keywords_count} слов, {examples_count} прим.")
else:
    print("   ❌ Нет активных пользователей")

# 2. Проверяем режимы пользователей
print("\n2. Режимы пользователей:")
for district_name, users_count, _, _ in active_stats[:5]:
    # Получаем ID района
    districts = db.get_all_districts()
    district_id = next((d_id for d_id, d_name in districts if d_name == district_name), None)
    
    if district_id:
        users = db.get_district_users(district_id)
        for user_id in users[:3]:  # Первые 3
            mode = db.get_user_mode(user_id)
            print(f"   Пользователь {user_id}: режим={mode}")

# 3. Тестируем оптимизацию
print("\n3. Запуск оптимизации...")
results = optimize_all_districts(db)

if results:
    print(f"   ✅ Оптимизировано районов: {len(results)}")
    for district_id, district_name, users_count, keywords_count, examples_count in results[:5]:
        print(f"   📍 {district_name}:")
        print(f"      👥 {users_count} пользователей")
        print(f"      🔑 {keywords_count} оптимизированных слов")
        print(f"      🤖 {examples_count} оптимизированных примеров")
else:
    print("   ❌ Нет районов для оптимизации")

# 4. Проверяем оптимизированные данные
print("\n4. Проверка оптимизированных данных:")
if results:
    for district_id, district_name, users_count, keywords_count, examples_count in results[:3]:
        opt_keywords = db.get_optimized_keywords(district_id)
        opt_examples_count = db.get_optimized_examples_count(district_id)
        
        print(f"\n   📍 {district_name}:")
        print(f"      Оптимизированные слова: {opt_keywords[:5] if opt_keywords else 'нет'}")
        print(f"      Количество ML примеров: {opt_examples_count}")

# 5. Тест переключения режима
print("\n5. Тест переключения режима:")
if active_stats:
    district_name, _, _, _ = active_stats[0]
    districts = db.get_all_districts()
    district_id = next((d_id for d_id, d_name in districts if d_name == district_name), None)
    
    if district_id:
        users = db.get_district_users(district_id)
        if users:
            test_user = users[0]
            
            # Текущий режим
            current_mode = db.get_user_mode(test_user)
            print(f"   Пользователь {test_user}: текущий режим = {current_mode}")
            
            # Переключаем
            new_mode = 'optimized' if current_mode == 'personal' else 'personal'
            db.set_user_mode(test_user, new_mode)
            
            # Проверяем
            check_mode = db.get_user_mode(test_user)
            print(f"   После переключения: {check_mode}")
            print(f"   ✅ Переключение работает!" if check_mode == new_mode else "   ❌ Ошибка переключения")
            
            # Возвращаем обратно
            db.set_user_mode(test_user, current_mode)

print("\n" + "="*60)
print("ТЕСТ ЗАВЕРШЕН")
print("="*60)
