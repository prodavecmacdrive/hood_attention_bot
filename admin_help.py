# coding: utf-8
"""
Административные функции для оптимизации данных по районам
"""
import numpy as np
import logging
from typing import List, Tuple, Dict
from database import Database
from ml_matcher import MessageMatcher

logger = logging.getLogger(__name__)


def optimize_keywords_for_district(db: Database, district_id: int) -> int:
    """
    Усреднение ключевых слов для района
    
    Args:
        db: Объект базы данных
        district_id: ID района
        
    Returns:
        Количество оптимизированных ключевых слов
    """
    try:
        # 1. Получаем всех пользователей района
        users = db.get_district_users(district_id)
        
        if not users:
            logger.info(f"Нет пользователей для района {district_id}")
            return 0
        
        # 2. Считаем частоту каждого ключевого слова
        keyword_freq: Dict[str, int] = {}
        for user_id in users:
            keywords = db.get_user_keywords(user_id)
            for keyword in keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        if not keyword_freq:
            logger.info(f"Нет ключевых слов для района {district_id}")
            return 0
        
        # 3. Удаляем старые оптимизированные данные
        db.clear_optimized_keywords(district_id)
        
        # 4. Сохраняем топ-20 самых популярных
        total_users = len(users)
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        for keyword, count in sorted_keywords:
            weight = count / total_users  # Процент пользователей использующих это слово
            db.add_optimized_keyword(district_id, keyword, count, weight)
        
        logger.info(f"Оптимизировано {len(sorted_keywords)} ключевых слов для района {district_id}")
        return len(sorted_keywords)
        
    except Exception as e:
        logger.error(f"Ошибка оптимизации ключевых слов для района {district_id}: {e}", exc_info=True)
        return 0


def optimize_ml_for_district(db: Database, district_id: int) -> int:
    """
    Усреднение ML примеров для района через кластеризацию
    
    Args:
        db: Объект базы данных
        district_id: ID района
        
    Returns:
        Количество оптимизированных примеров
    """
    try:
        # 1. Получаем все примеры всех пользователей района
        users = db.get_district_users(district_id)
        
        if not users:
            logger.info(f"Нет пользователей для района {district_id}")
            return 0
        
        all_examples: List[Tuple[str, bytes]] = []
        
        for user_id in users:
            examples = db.get_user_examples(user_id)
            all_examples.extend(examples)
        
        if len(all_examples) < 2:
            logger.info(f"Недостаточно примеров для кластеризации в районе {district_id} ({len(all_examples)} < 2)")
            return 0
        
        # 2. Извлекаем embeddings
        embeddings = []
        valid_examples = []
        
        for text, embedding_bytes in all_examples:
            try:
                # Используем правильный метод десериализации
                embedding = MessageMatcher.deserialize_embedding(embedding_bytes)
                
                # Проверяем на NaN и бесконечность
                if not np.isnan(embedding).any() and not np.isinf(embedding).any():
                    embeddings.append(embedding)
                    valid_examples.append((text, embedding_bytes))
                else:
                    logger.warning(f"Пропущен пример с NaN/Inf значениями: {text[:50]}")
            except Exception as e:
                logger.warning(f"Ошибка обработки embedding: {e}")
                continue
        
        if len(valid_examples) < 2:
            logger.info(f"Недостаточно валидных примеров в районе {district_id} ({len(valid_examples)} < 2)")
            return 0
        
        embeddings_matrix = np.vstack(embeddings)
        
        # 3. Кластеризация (находим до 10 типичных примеров)
        from sklearn.cluster import KMeans
        
        n_clusters = min(10, len(valid_examples))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(embeddings_matrix)
        
        # 4. Удаляем старые оптимизированные примеры
        db.clear_optimized_examples(district_id)
        
        # 5. Сохраняем центроиды кластеров как оптимизированные примеры
        for cluster_id, centroid in enumerate(kmeans.cluster_centers_):
            # Находим ближайший реальный пример к центроиду
            distances = np.linalg.norm(embeddings_matrix - centroid, axis=1)
            closest_idx = np.argmin(distances)
            closest_example_text = valid_examples[closest_idx][0]
            closest_example_embedding = valid_examples[closest_idx][1]
            
            db.add_optimized_example(
                district_id,
                closest_example_text,
                closest_example_embedding,
                cluster_id,
                weight=1.0
            )
        
        logger.info(f"Оптимизировано {n_clusters} ML примеров для района {district_id}")
        return n_clusters
        
    except Exception as e:
        logger.error(f"Ошибка оптимизации ML для района {district_id}: {e}", exc_info=True)
        return 0


def optimize_all_districts(db: Database) -> List[Tuple[int, str, int, int, int]]:
    """
    Оптимизация всех районов
    
    Returns:
        List[(district_id, district_name, users_count, keywords_count, examples_count)]
    """
    results = []
    
    try:
        districts = db.get_all_districts()
        
        for district_id, district_name in districts:
            users_count = db.get_district_users_count(district_id)
            
            if users_count == 0:
                continue  # Пропускаем районы без пользователей
            
            # Оптимизация ключевых слов
            keywords_count = optimize_keywords_for_district(db, district_id)
            
            # Оптимизация ML примеров
            examples_count = optimize_ml_for_district(db, district_id)
            
            # Сохраняем лог
            db.log_optimization(district_id, users_count, keywords_count, examples_count)
            
            results.append((district_id, district_name, users_count, keywords_count, examples_count))
        
        logger.info(f"Оптимизация завершена для {len(results)} районов")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка массовой оптимизации: {e}", exc_info=True)
        return results
