"""
Тест системы обратной связи (Feedback System)
"""

from database import Database
from ml_matcher import get_matcher, MessageMatcher

def test_feedback_system():
    """Тестирование полного цикла работы feedback системы"""
    
    print("=" * 60)
    print("ТЕСТ СИСТЕМЫ ОБРАТНОЙ СВЯЗИ")
    print("=" * 60)
    
    db = Database()
    matcher = get_matcher()
    test_user_id = 460359909
    
    # Очищаем старые данные
    print("\n1️⃣ Очистка старых данных...")
    db.clear_user_examples(test_user_id)
    db.clear_negative_examples(test_user_id)
    print("   ✅ Очищено")
    
    # Добавляем позитивные примеры
    print("\n2️⃣ Добавление позитивных примеров...")
    positive_texts = [
        "РСЗО по області Шишковка",
        "Удар по району Жуки",
        "Пятихатки під обстрілом"
    ]
    
    for text in positive_texts:
        embedding = matcher.encode_text(text)
        embedding_bytes = MessageMatcher.serialize_embedding(embedding)
        db.add_user_example(test_user_id, text, embedding_bytes)
        print(f"   ✅ Добавлен: {text}")
    
    pos_count = db.get_user_examples_count(test_user_id)
    print(f"   📊 Всего позитивных примеров: {pos_count}")
    
    # Добавляем негативные примеры
    print("\n3️⃣ Добавление негативных примеров (дизлайки)...")
    negative_texts = [
        "РСЗО по області в режимі ПВО",
        "Повітряна тривога в сусідньому районі",
        "Учения противовоздушной обороны"
    ]
    
    for text in negative_texts:
        embedding = matcher.encode_text(text)
        embedding_bytes = MessageMatcher.serialize_embedding(embedding)
        db.add_negative_example(test_user_id, text, embedding_bytes)
        print(f"   ✅ Добавлен: {text}")
    
    neg_count = db.get_negative_examples_count(test_user_id)
    print(f"   📊 Всего негативных примеров: {neg_count}")
    
    # Тестовые сообщения для проверки фильтрации
    print("\n4️⃣ Проверка фильтрации новых сообщений...")
    
    test_messages = [
        ("РСЗО по області біля села Шишковка", True),  # Должно пройти
        ("РСЗО по області в режимі бойової готовності", False),  # Должно заблокировать
        ("Удар по населённому пункту Жуки", True),  # Должно пройти
        ("Повітряна тривога в районі Пятихатки", True),  # Должно пройти
        ("Тривога в сусідніх населених пунктах", False)  # Должно заблокировать
    ]
    
    # Загружаем примеры
    positive_examples = db.get_user_examples(test_user_id)
    negative_examples = db.get_negative_examples(test_user_id)
    
    positive_embeddings = [
        MessageMatcher.deserialize_embedding(emb_bytes)
        for _, emb_bytes in positive_examples
    ]
    
    negative_embeddings = [
        MessageMatcher.deserialize_embedding(emb_bytes)
        for _, emb_bytes in negative_examples
    ]
    
    print("\n   Тестирование:")
    correct_predictions = 0
    
    for message, should_pass in test_messages:
        # Проверка позитивного совпадения
        text_embedding = matcher.encode_text(message)
        
        max_positive_sim = max(
            matcher.cosine_similarity(text_embedding, pos_emb)
            for pos_emb in positive_embeddings
        )
        
        max_negative_sim = max(
            matcher.cosine_similarity(text_embedding, neg_emb)
            for neg_emb in negative_embeddings
        )
        
        # Логика фильтрации
        matched_positive = max_positive_sim > 0.75
        blocked_by_negative = False
        
        if matched_positive:
            if max_negative_sim > 0.85:
                blocked_by_negative = True
            elif max_positive_sim < 0.80 and max_negative_sim > 0.70:
                blocked_by_negative = True
        
        will_pass = matched_positive and not blocked_by_negative
        
        # Проверяем результат
        is_correct = (will_pass == should_pass)
        status_emoji = "✅" if is_correct else "❌"
        action = "ПРОПУСТИТЬ" if will_pass else "БЛОКИРОВАТЬ"
        expected = "пропустить" if should_pass else "блокировать"
        
        if is_correct:
            correct_predictions += 1
        
        print(f"\n   {status_emoji} '{message[:50]}...'")
        print(f"      Позитив: {max_positive_sim:.2%} | Негатив: {max_negative_sim:.2%}")
        print(f"      Решение: {action} (ожидалось: {expected})")
    
    # Итоги
    print("\n" + "=" * 60)
    accuracy = (correct_predictions / len(test_messages)) * 100
    print(f"📊 РЕЗУЛЬТАТЫ: {correct_predictions}/{len(test_messages)} корректных ({accuracy:.0f}%)")
    
    if accuracy >= 80:
        print("✅ ТЕСТ ПРОЙДЕН!")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
    
    print("=" * 60)
    
    # Очистка
    print("\n5️⃣ Очистка тестовых данных...")
    db.clear_user_examples(test_user_id)
    db.clear_negative_examples(test_user_id)
    print("   ✅ Данные очищены")


if __name__ == "__main__":
    test_feedback_system()
