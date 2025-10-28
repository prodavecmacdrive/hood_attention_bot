# coding: utf-8
"""
Тест добавления ML примера напрямую
"""
from database import Database
from ml_matcher import get_matcher, MessageMatcher

db = Database()
matcher = get_matcher()

user_id = 460359909

print("=== Тест добавления ML примера ===\n")

# Проверяем текущее количество
current_count = db.get_user_examples_count(user_id)
print(f"Текущее количество примеров: {current_count}")

# Добавляем тестовый пример
test_text = "Тестовое сообщение для проверки сохранения ML примера в базу данных"
print(f"\nДобавляем пример: '{test_text[:50]}...'")

# Создаем embedding
embedding = matcher.encode_text(test_text)
print(f"Embedding создан: размер={embedding.shape}, dtype={embedding.dtype}")
print(f"Первые 5 значений: {embedding[:5]}")

# Сериализуем
embedding_bytes = MessageMatcher.serialize_embedding(embedding)
print(f"Сериализован: {len(embedding_bytes)} байт")

# Сохраняем
result = db.add_user_example(user_id, test_text, embedding_bytes)
print(f"Результат сохранения: {result}")

# Проверяем
new_count = db.get_user_examples_count(user_id)
print(f"\nНовое количество примеров: {new_count}")

if new_count > current_count:
    print("✅ Пример успешно сохранен!")
    
    # Читаем обратно
    examples = db.get_user_examples(user_id)
    print(f"\nВсе примеры пользователя {user_id}:")
    for i, (text, emb_bytes) in enumerate(examples, 1):
        emb = MessageMatcher.deserialize_embedding(emb_bytes)
        has_nan = any(x != x for x in emb)  # NaN != NaN
        print(f"  {i}. {text[:50]}... (embedding: {emb.shape}, NaN: {has_nan})")
else:
    print("❌ Пример НЕ сохранен!")
