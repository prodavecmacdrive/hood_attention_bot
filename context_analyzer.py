"""
Контекстный анализатор для извлечения информации из цепочек сообщений.
"""
import logging
import re
from collections import Counter
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np

from database import Database

logger = logging.getLogger(__name__)

class ContextAnalyzer:
    def __init__(self, db: Database):
        self.db = db
        self.model = None  # Ленивая загрузка
        self.threat_embeddings = {}
        self.districts = []

    def _lazy_load_model(self):
        """Ленивая загрузка модели и данных"""
        if self.model is None:
            logger.info("Загрузка модели для ContextAnalyzer...")
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            # Шаблоны угроз
            self.threat_types = {
                'шахед': ['шахед', 'дрон', 'бпла', 'герань', 'мопед'],
                'ракета': ['ракета', 'крилата', 'калібр', 'іскандер', 'x-101', 'x-59', 'кинджал'],
                'рсзо': ['рсзо', 'град', 'торнадо', 'смерч', 'ураган'],
                'артилерія': ['артилерія', 'обстріл', 'міномет', 'ствольна'],
                'авіабомба': ['каб', 'фаб', 'авіабомба'],
            }
            
            # Embeddings для типов угроз
            self.threat_embeddings = {
                threat_type: self.model.encode(' '.join(keywords))
                for threat_type, keywords in self.threat_types.items()
            }
            
            # Загружаем районы из БД
            self.districts = [name.lower() for _, name in self.db.get_all_districts()]
            logger.info("ContextAnalyzer инициализирован.")

    def analyze_context(self, trigger_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует контекст вокруг сообщения-триггера, используя исторические данные.
        """
        self._lazy_load_model()
        
        # 1. Получаем недавние сообщения из истории
        recent_messages = self.db.get_recent_historical_messages(minutes_ago=30)
        if not recent_messages:
            return None

        # 2. Находим наиболее релевантные сообщения (событие)
        event_messages = self._find_event_cluster(recent_messages, trigger_message)
        if not event_messages:
            return None

        # 3. Анализируем кластер сообщений
        context_text = ' '.join([msg[2] for msg in event_messages])
        
        threat_type, threat_confidence = self._detect_threat_type(context_text)
        locations = self._extract_locations(context_text)
        direction = self._extract_direction(context_text)
        
        # 4. Формируем результат
        summary = self._generate_summary(threat_type, locations, direction)
        
        # Находим ссылки на самые релевантные сообщения
        related_links = self._get_related_links(event_messages, trigger_message)

        return {
            'threat_type': threat_type,
            'locations': locations,
            'direction': direction,
            'summary': summary,
            'related_links': related_links,
            'confidence': threat_confidence
        }

    def _find_event_cluster(self, messages: List[Tuple], trigger_message: Dict[str, Any]) -> List[Tuple]:
        """
        Находит группу сообщений, относящихся к одному событию, используя семантическую близость.
        """
        trigger_embedding = self.model.encode(trigger_message['text'])
        
        # Добавляем embedding для триггера к остальным
        all_embeddings = [trigger_embedding]
        for msg in messages:
            if msg[4]: # msg[4] is embedding
                all_embeddings.append(np.frombuffer(msg[4], dtype=np.float32))
            else:
                # Если embedding не был предрасчитан
                all_embeddings.append(self.model.encode(msg[2]))

        # Простое кластеризация по сходству с триггером
        cluster = []
        for i, msg in enumerate(messages):
            # Считаем сходство с триггером
            similarity = self._cosine_similarity(trigger_embedding, all_embeddings[i+1])
            if similarity > 0.70:  # Порог для включения в кластер
                cluster.append(msg)
        
        return cluster

    def _detect_threat_type(self, context_text: str) -> (str, float):
        """Определяет тип угрозы по тексту."""
        context_lower = context_text.lower()
        
        # Считаем упоминания ключевых слов
        counts = Counter()
        for threat, keywords in self.threat_types.items():
            for kw in keywords:
                counts[threat] += context_lower.count(kw)
        
        if not counts:
            return None, 0.0
            
        # Выбираем наиболее частый тип угрозы
        best_match, count = counts.most_common(1)[0]
        
        # Уверенность зависит от количества упоминаний
        confidence = min(1.0, count / 5.0) # 100% уверенность после 5 упоминаний
        
        return best_match, confidence

    def _extract_locations(self, text: str) -> List[str]:
        """Извлекает упоминания районов/локаций."""
        text_lower = text.lower()
        found_locations = set()
        
        for district in self.districts:
            if district in text_lower:
                found_locations.add(district.capitalize())
        
        return list(found_locations)

    def _extract_direction(self, text: str) -> str:
        """Извлекает информацию о направлении."""
        direction_patterns = [
            r'заходить з боку (.+?)(?:\.|,|$)',
            r'летить (в бік|на) (.+?)(?:\.|,|$)',
            r'напрямок (.+?)(?:\.|,|$)',
            r'курс на (.+?)(?:\.|,|$)',
            r'через (.+?)(?:\.|,|$)',
        ]
        
        text_lower = text.lower()
        for pattern in direction_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(0)
        
        return None

    def _generate_summary(self, threat_type, locations, direction):
        """Генерирует краткое описание угрозы."""
        parts = []
        if threat_type:
            parts.append(f"🎯 **Тип:** {threat_type.capitalize()}")
        if locations:
            parts.append(f"📍 **Локації:** {', '.join(locations)}")
        if direction:
            parts.append(f"➡️ **Напрямок:** {direction}")
        
        return '\n'.join(parts) if parts else "Контекст не визначено"

    def _get_related_links(self, event_messages: List[Tuple], trigger_message: Dict[str, Any]) -> List[str]:
        """Возвращает ссылки на 3 наиболее релевантных сообщения из кластера."""
        if not event_messages:
            return []
            
        trigger_embedding = self.model.encode(trigger_message['text'])
        
        scored_messages = []
        for msg in event_messages:
            msg_embedding = np.frombuffer(msg[4], dtype=np.float32) if msg[4] else self.model.encode(msg[2])
            similarity = self._cosine_similarity(trigger_embedding, msg_embedding)
            scored_messages.append((msg, similarity))
            
        scored_messages.sort(key=lambda x: x[1], reverse=True)
        
        links = []
        for msg, score in scored_messages[:3]:
            link = f"https://t.me/{msg[0].lstrip('@')}/{msg[1]}"
            links.append(link)
            
        return links

    def _cosine_similarity(self, emb1, emb2):
        """Вычисляет косинусное сходство."""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
