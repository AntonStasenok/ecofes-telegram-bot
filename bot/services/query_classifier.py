# bot/services/query_classifier.py
import re
from typing import Dict, Tuple

class QueryClassifier:
    """Классификатор запросов для определения типа ответа"""
    
    def __init__(self):
        # Паттерны для разных типов запросов
        self.greeting_patterns = [
            r'\b(привет|здравствуй|добр\w+ день|добр\w+ утро|добр\w+ вечер|хай|hi|hello)\b',
            r'\b(как дела|как поживаеш|что как)\b',
            r'^(привет|hi|hello|хай)$',
        ]
        
        self.about_patterns = [
            r'\b(кто ты|что ты|расскажи о себе|о компании|кто вы|что вы)\b',
            r'\b(ecofes|экофес|ваша компания|твоя компания)\b',
            r'\b(чем занимаетесь|что делаете)\b',
        ]
        
        self.technical_patterns = [
            r'\b(масло|смазк\w+|двигател\w+|мотор\w+|вязкость|SAE|API|ACEA)\b',
            r'\b(автомобил\w+|машин\w+|транспорт\w+|техник\w+)\b',
            r'\b(замен\w+|интервал\w+|расход\w+|температур\w+)\b',
            r'\b(синтетик\w+|минерал\w+|полусинтетик\w+)\b',
            r'\b(фильтр\w+|присадк\w+|антифриз\w+|охлаждающ\w+)\b',
            r'\b(грузовик\w+|автобус\w+|спецтехник\w+|тракт\w+)\b',
        ]
        
        self.simple_patterns = [
            r'\b(спасибо|благодар\w+|хорошо|отлично|понятно|ясно)\b',
            r'\b(пока|до свидания|увидимся)\b',
            r'\b(да|нет|не знаю|может быть)\b',
        ]
    
    def classify_query(self, text: str) -> Tuple[str, float]:
        """
        Классифицирует запрос и возвращает тип и уровень уверенности
        
        Returns:
            Tuple[str, float]: (тип_запроса, уверенность_0_1)
        """
        text_lower = text.lower().strip()
        
        # Проверяем приветствия
        for pattern in self.greeting_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return "greeting", 0.9
        
        # Проверяем вопросы о компании/боте
        for pattern in self.about_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return "about", 0.8
        
        # Проверяем простые ответы
        for pattern in self.simple_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return "simple", 0.8
        
        # Проверяем технические вопросы
        technical_score = 0
        for pattern in self.technical_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                technical_score += 1
        
        if technical_score >= 2:
            return "technical", 0.9
        elif technical_score == 1:
            return "technical", 0.6
        
        # Если длинный вопрос без технических терминов - скорее всего общий
        if len(text.split()) > 5:
            return "general", 0.4
        
        # По умолчанию - неопределенный
        return "unknown", 0.3
    
    def get_confidence_threshold(self, query_type: str) -> float:
        """Возвращает минимальный порог уверенности для использования RAG"""
        thresholds = {
            "greeting": 0.0,  # Никогда не используем RAG
            "about": 0.0,     # Никогда не используем RAG  
            "simple": 0.0,    # Никогда не используем RAG
            "technical": 0.5, # Используем RAG только при высокой уверенности
            "general": 0.6,   # Осторожно используем RAG
            "unknown": 0.7    # Очень осторожно
        }
        return thresholds.get(query_type, 0.7)
