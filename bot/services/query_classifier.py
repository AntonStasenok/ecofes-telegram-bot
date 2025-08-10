# bot/services/query_classifier.py
import re
from typing import Dict, Tuple, List

class QueryClassifier:
    """Улучшенный классификатор запросов для определения типа ответа"""
    
    def __init__(self):
        # Паттерны для разных типов запросов
        self.greeting_patterns = [
            r'\b(привет|здравствуй|добр\w+ день|добр\w+ утро|добр\w+ вечер|хай|hi|hello)\b',
            r'\b(как дела|как поживаеш|что как)\b',
            r'^(привет|hi|hello|хай)$',
        ]
        
        self.about_patterns = [
            r'\b(кто ты|что ты|расскажи о себе|о компании|кто вы|что вы)\b',
            r'\b(ваша компания|твоя компания|вашей компан\w+|вашей кампан\w+)\b',
            r'\b(чем занимаетесь|что делаете|твоей компан\w+)\b',
            r'\b(ecofes|экофес|eco\s*fes|эко\s*фес)\b',
            r'\b(производител\w+|завод\w+|офис\w+)\b',
        ]
        
        # Расширенные технические паттерны на основе документации
        self.technical_patterns = [
            # Общие термины масел
            r'\b(мас\w+|смазк\w+|двигател\w+|мото\w+|вязкос\w+|fes|фэс|фес)\b',
            
            # Стандарты и допуски
            r'\b(SAE|sae|API|api|ACEA|acea|JASO|jaso|ISO|iso)\b',
            r'\b(SP|SN|CF|CJ|CI|SL|DL|FD|FB|MA|TD|EDG)\b',
            
            # Типы транспорта и техники
            r'\b(автомобил\w+|машин\w+|транспор\w+|техни\w+|грузов\w+|коммерч\w+)\b',
            r'\b(мотоцикл\w+|мотороллер\w+|байк\w+|мототехни\w+|снегоход\w+)\b',
            r'\b(лодк\w+|катер\w+|водн\w+ транспор\w+|морск\w+|речн\w+)\b',
            r'\b(трактор\w+|комбайн\w+|сельхоз\w+|агротехни\w+|спецтехни\w+)\b',
            r'\b(компрессор\w+|редуктор\w+|гидравли\w+|холодиль\w+)\b',
            r'\b(эскалатор\w+|лифт\w+|конвейер\w+|промышлен\w+|индустри\w+)\b',
            
            # Производители и марки
            r'\b(кама\w+|эскава\w+|мерсе\w+|бмв\w+|маз\w+|ямз|автоваз|умз|змз)\b',
            r'\b(volvo|mb|mercedes|bmw|vw|volkswagen|ford|porsche|gm)\b',
            r'\b(caterpillar|cat|cummins|mack|man|scania|renault|iveco)\b',
            
            # Характеристики и свойства
            r'\b(синтетик\w+|минерал\w+|полусинтетик\w+|всесезон\w+)\b',
            r'\b(замен\w+|интервал\w+|преиму\w+|расход\w+|температур\w+)\b',
            r'\b(фильтр\w+|присадк\w+|антифриз\w+|охлаждающ\w+)\b',
            r'\b(вязкост\w+|загущ\w+|деструкц\w+|износ\w+|защит\w+)\b',
            
            # Типы двигателей и систем
            r'\b(2т|4т|двухтакт\w+|четырехтакт\w+|дизел\w+|бензин\w+)\b',
            r'\b(турбо\w+|атмосфер\w+|наддув\w+|впрыск\w+)\b',
            r'\b(газопоршн\w+|гпу|ГПУ|газомотор\w+|гмт|ГМТ)\b',
            r'\b(кпг|КПГ|снг|СНГ|битоплив\w+)\b',
            
            # Области применения из документации
            r'\b(racing|рейсинг\w+|дрифт\w+|спринт\w+|ралли|драг)\b',
            r'\b(aqua|snow|moto|hp|ultra|premium|drive)\b',
        ]
        
        self.simple_patterns = [
            r'\b(спасибо|благодар\w+|хорошо|отлично|понятно|ясно)\b',
            r'\b(пока|до свидания|увидимся)\b',
            r'\b(да|нет|не знаю|может быть)\b',
            r'^(ок|ok|окей|хм|м|да|нет)$',
        ]
        
        # Паттерны для запроса цен и покупки
        self.commercial_patterns = [
            r'\b(цена|цены|стоим\w+|сколько\s+стоит|купить|заказ\w+|приобрес\w+)\b',
            r'\b(где\s+купить|как\s+купить|прайс|дилер\w+|представител\w+)\b',
            r'\b(доставк\w+|оплат\w+|скидк\w+|опт\w+|розниц\w+)\b',
        ]
        
        # Паттерны для подбора масла
        self.selection_patterns = [
            r'\b(подбор\w+|подойд\w+|выбр\w+|посовет\w+|рекоменд\w+)\b',
            r'\b(какое\s+масло|что\s+лучше|что\s+подойдет|подскаж\w+)\b',
            r'\b(у\s+меня|для\s+моей|на\s+мою|в\s+мой)\b',
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
                return "about", 0.85
        
        # Проверяем простые ответы
        for pattern in self.simple_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return "simple", 0.8
        
        # Проверяем коммерческие запросы
        commercial_score = 0
        for pattern in self.commercial_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                commercial_score += 1
        
        if commercial_score >= 1:
            return "commercial", 0.8
        
        # Проверяем запросы на подбор
        selection_score = 0
        for pattern in self.selection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                selection_score += 1
        
        # Проверяем технические термины
        technical_score = 0
        for pattern in self.technical_patterns:
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            technical_score += matches
        
        # Определяем тип на основе баллов
        if selection_score >= 1 and technical_score >= 1:
            return "selection", 0.9  # Подбор с техническими терминами
        elif selection_score >= 1:
            return "selection", 0.7   # Общий запрос на подбор
        elif technical_score >= 3:
            return "technical", 0.9  # Много технических терминов
        elif technical_score >= 2:
            return "technical", 0.75 # Несколько технических терминов  
        elif technical_score == 1:
            return "technical", 0.5  # Один технический термин
        
        # Если длинный вопрос без технических терминов - скорее всего общий
        if len(text.split()) > 5:
            return "general", 0.4
        
        # По умолчанию - неопределенный
        return "unknown", 0.3
    
    def get_confidence_threshold(self, query_type: str) -> float:
        """Возвращает минимальный порог уверенности для использования RAG"""
        thresholds = {
            "greeting": 0.0,     # Никогда не используем RAG
            "about": 0.0,        # Никогда не используем RAG  
            "simple": 0.0,       # Никогда не используем RAG
            "commercial": 0.5,   # Можем использовать RAG для цен/дилеров
            "selection": 0.6,    # Используем RAG для подбора масел
            "technical": 0.5,    # Используем RAG только при высокой уверенности
            "general": 0.6,      # Осторожно используем RAG
            "unknown": 0.7       # Очень осторожно
        }
        return thresholds.get(query_type, 0.7)
    
    def get_query_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова для улучшения RAG поиска"""
        keywords = []
        text_lower = text.lower()
        
        # Технические термины
        tech_keywords = [
            "5W-30", "5W-40", "10W-40", "0W-20", "0W-30", "15W-40", "20W-50",
            "API", "ACEA", "JASO", "SAE", "ISO", "синтетика", "полусинтетика",
            "мотоцикл", "снегоход", "лодка", "грузовик", "легковой", 
            "компрессор", "редуктор", "гидравлика", "трансмиссия"
        ]
        
        for keyword in tech_keywords:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        
        return keywords
