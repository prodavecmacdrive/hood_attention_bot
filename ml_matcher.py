"""
ML-based message matching using sentence embeddings
Использует sentence-transformers для семантического поиска похожих сообщений
"""

import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple
import pickle

logger = logging.getLogger(__name__)


class MessageMatcher:
    """Класс для семантического сравнения сообщений"""
    
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Инициализация модели
        
        Args:
            model_name: Название модели. Варианты:
                - 'paraphrase-multilingual-MiniLM-L12-v2' (80MB, быстрая)
                - 'cointegrated/rubert-tiny2' (120MB, лучше для русского)
        """
        try:
            logger.info(f"Загрузка ML модели: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info("ML модель загружена успешно")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        Конвертирует текст в вектор (embedding)
        
        Args:
            text: Текст сообщения
            
        Returns:
            numpy array с векторным представлением текста
        """
        try:
            # Нормализуем текст
            text = text.strip()
            if not text:
                return np.zeros(384)  # Возвращаем нулевой вектор для пустого текста
            
            # Получаем embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Ошибка кодирования текста: {e}")
            return np.zeros(384)
    
    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Вычисляет косинусное сходство между двумя векторами
        
        Args:
            embedding1: Первый вектор
            embedding2: Второй вектор
            
        Returns:
            Значение от 0 до 1 (1 = идентичны, 0 = полностью разные)
        """
        try:
            # Нормализуем векторы
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Вычисляем косинусное сходство
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Возвращаем значение от 0 до 1
            return float(max(0.0, min(1.0, similarity)))
        except Exception as e:
            logger.error(f"Ошибка вычисления сходства: {e}")
            return 0.0
    
    def find_best_match(
        self, 
        text: str, 
        examples: List[Tuple[str, np.ndarray]]
    ) -> Tuple[float, str]:
        """
        Находит наиболее похожий пример из списка
        
        Args:
            text: Текст для проверки
            examples: Список кортежей (текст примера, embedding)
            
        Returns:
            (максимальное сходство, текст наиболее похожего примера)
        """
        if not examples:
            return 0.0, ""
        
        try:
            text_embedding = self.encode_text(text)
            
            max_similarity = 0.0
            best_example = ""
            
            for example_text, example_embedding in examples:
                similarity = self.cosine_similarity(text_embedding, example_embedding)
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_example = example_text
            
            return max_similarity, best_example
        except Exception as e:
            logger.error(f"Ошибка поиска совпадения: {e}")
            return 0.0, ""
    
    def is_similar(
        self, 
        text: str, 
        examples: List[np.ndarray], 
        threshold: float = 0.75
    ) -> bool:
        """
        Проверяет, похож ли текст хотя бы на один из примеров
        
        Args:
            text: Текст для проверки
            examples: Список embeddings примеров
            threshold: Порог сходства (0-1). По умолчанию 0.75 (75%)
            
        Returns:
            True если найдено совпадение, False иначе
        """
        if not examples:
            return False
        
        try:
            text_embedding = self.encode_text(text)
            
            for example_embedding in examples:
                similarity = self.cosine_similarity(text_embedding, example_embedding)
                
                if similarity >= threshold:
                    logger.debug(f"Найдено совпадение с порогом {threshold}: {similarity:.2f}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки сходства: {e}")
            return False
    
    @staticmethod
    def serialize_embedding(embedding: np.ndarray) -> bytes:
        """Сериализует embedding для хранения в БД"""
        return pickle.dumps(embedding)
    
    @staticmethod
    def deserialize_embedding(data: bytes) -> np.ndarray:
        """Десериализует embedding из БД"""
        return pickle.loads(data)


# Глобальный экземпляр (ленивая инициализация)
_matcher_instance = None


def get_matcher() -> MessageMatcher:
    """Получить глобальный экземпляр MessageMatcher (singleton)"""
    global _matcher_instance
    
    if _matcher_instance is None:
        _matcher_instance = MessageMatcher()
    
    return _matcher_instance
