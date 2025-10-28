# Система обратной связи (Feedback System)

## Описание

Система обратной связи позволяет пользователям оценивать пересылаемые сообщения с помощью кнопок 👍/👎, чтобы улучшить качество фильтрации и уменьшить количество ложных срабатываний.

## Проблема

При использовании ML-поиска по семантической схожести могут возникать **ложные срабатывания** (false positives):

**Пример:**
- ✅ "РСЗО по області" - релевантное сообщение
- ❌ "РСЗО по області в режимі ПВО" - НЕ релевантное (ложное срабатывание)

Оба сообщения семантически похожи, но имеют разный смысл в контексте угрозы.

## Решение: Гибридный подход

### 1. Негативные примеры (Negative Examples)

- Пользователь нажимает 👎 на нерелевантном сообщении
- Система создает embedding и сохраняет как **негативный пример**
- При фильтрации новых сообщений проверяется сходство с негативными примерами
- Если сообщение похоже на негативный пример → блокируется

### 2. Логика фильтрации

**Условия блокировки:**

1. **Сильное негативное совпадение:**
   ```
   max_negative_similarity > 0.85 → БЛОК
   ```

2. **Слабое позитивное + среднее негативное:**
   ```
   max_positive_similarity < 0.80 AND max_negative_similarity > 0.70 → БЛОК
   ```

**Условия пропуска:**
```
(matched_keywords OR matched_ml) AND NOT blocked_by_negative → ОТПРАВИТЬ
```

## Архитектура

### База данных

**Таблица: `user_negative_examples`**
```sql
CREATE TABLE IF NOT EXISTS user_negative_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    example_text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
)
```

**Методы БД:**
- `add_negative_example(user_id, text, embedding)` - добавить негативный пример
- `get_negative_examples(user_id)` - получить все негативные примеры
- `get_negative_examples_count(user_id)` - количество негативных примеров
- `clear_negative_examples(user_id)` - очистить все негативные примеры

### Кэш сообщений

```python
message_cache = {}  # {(user_id, msg_id): message_text}
```

Используется для хранения текстов сообщений, пока пользователь не нажмет кнопку обратной связи.

## Workflow

### 1. Отправка сообщения пользователю

```python
# При совпадении по ключевым словам или ML
feedback_buttons = [
    Button.inline("👍 Полезно", f"feedback_like_{msg_id}"),
    Button.inline("👎 Не то", f"feedback_dislike_{msg_id}")
]

# Сохраняем текст в кэш
message_cache[(user_id, msg_id)] = message_text

# Отправляем с кнопками
await bot_client.send_message(user_id, text, buttons=feedback_buttons)
```

### 2. Обработка 👍 (Like)

```python
@bot_client.on(events.CallbackQuery(pattern=rb'feedback_like_(\d+)'))
async def feedback_like_handler(event):
    # Удаляем кнопки
    await event.edit(buttons=None)
    await event.answer("✅ Спасибо за отзыв!")
    
    # Очищаем кэш
    message_cache.pop((user_id, msg_id), None)
```

### 3. Обработка 👎 (Dislike) - сохранение негативного примера

```python
@bot_client.on(events.CallbackQuery(pattern=rb'feedback_dislike_(\d+)'))
async def feedback_dislike_handler(event):
    # Получаем текст из кэша
    message_text = message_cache.get((user_id, msg_id))
    
    # Создаем embedding
    embedding = matcher.encode_text(message_text)
    embedding_bytes = MessageMatcher.serialize_embedding(embedding)
    
    # Сохраняем в БД
    db.add_negative_example(user_id, message_text, embedding_bytes)
    
    # Удаляем кнопки и очищаем кэш
    await event.edit(buttons=None)
    message_cache.pop((user_id, msg_id), None)
```

### 4. Фильтрация новых сообщений

```python
# Проверка 1: Ключевые слова
matched_keywords = ...

# Проверка 2: ML позитивные примеры
matched_ml = ...
ml_similarity = ...

# Проверка 3: Негативные примеры
if matched_keywords or matched_ml:
    negative_examples = db.get_negative_examples(user_id)
    
    if negative_examples:
        negative_embeddings = [deserialize(emb) for _, emb in negative_examples]
        text_embedding = matcher.encode_text(message_text)
        
        max_negative_similarity = max(
            matcher.cosine_similarity(text_embedding, neg_emb)
            for neg_emb in negative_embeddings
        )
        
        # Блокировка
        if max_negative_similarity > 0.85:
            blocked_by_negative = True
        elif ml_similarity < 0.80 and max_negative_similarity > 0.70:
            blocked_by_negative = True

# Отправка только если не заблокировано
if (matched_keywords or matched_ml) and not blocked_by_negative:
    await send_message(...)
```

## Команды пользователя

### `/dislikes_stats`
Показывает статистику негативных примеров:
```
👎 Негативные примеры (дизлайки):

Всего: 7

📋 Последние примеры:
• РСЗО по області в режимі ПВО
• Повідомлення про тривогу в сусідніх районах
• ...

...и ещё 2
```

### `/clear_dislikes`
Удаляет все негативные примеры пользователя.

## Будущие улучшения

### Классификатор (при наличии 30+ примеров)

Когда накопится достаточно позитивных и негативных примеров, можно обучить **бинарный классификатор**:

```python
from sklearn.linear_model import LogisticRegression

# X = все embeddings (позитивные + негативные)
# y = labels (1 = релевантно, 0 = нет)

classifier = LogisticRegression()
classifier.fit(X, y)

# При фильтрации:
prediction = classifier.predict_proba([text_embedding])[0][1]
if prediction > 0.7:
    send_message(...)
```

**Преимущества:**
- Более точное разделение релевантных/нерелевантных сообщений
- Автоматическая настройка границ принятия решений
- Учет сложных паттернов в данных

## Метрики эффективности

### Текущие пороги:
- `threshold_positive_ml = 0.75` - минимальное сходство с позитивными примерами
- `threshold_negative_strong = 0.85` - сильное негативное совпадение → блок
- `threshold_negative_medium = 0.70` - среднее негативное при слабом позитивном → блок

### Логи:
```
Сообщение переслано пользователю 123 [personal] (keywords: ['рсзо', 'область'], ML: 82%)
Сообщение заблокировано негативным примером для пользователя 123 (similarity: 91%)
Сообщение заблокировано (слабое позитивное 76%, сильное негативное 73%)
```

## Тестирование

### Сценарий 1: Добавление негативного примера

1. Настройте ключевое слово "РСЗО"
2. Получите сообщение "РСЗО по області в режимі ПВО"
3. Нажмите 👎
4. Проверьте: `/dislikes_stats` → должно быть 1
5. Отправьте похожее сообщение
6. Проверьте: сообщение должно быть заблокировано

### Сценарий 2: Очистка негативных примеров

1. Выполните `/clear_dislikes`
2. Проверьте: `/dislikes_stats` → должно быть 0
3. Отправьте ранее заблокированное сообщение
4. Проверьте: сообщение должно пройти

## Технические детали

### Embeddings
- Модель: `paraphrase-multilingual-MiniLM-L12-v2`
- Размерность: 384
- Сериализация: `pickle.dumps(embedding)`
- Десериализация: `pickle.loads(data)`

### Cosine Similarity
```python
def cosine_similarity(emb1, emb2):
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
```

### Производительность
- Проверка негативных примеров выполняется **только** если есть позитивное совпадение
- Embeddings вычисляются **один раз** для каждого сообщения
- Используется кэш для текстов сообщений (ограничен временем жизни)
