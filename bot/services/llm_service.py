# bot/services/llm_service.py
import httpx
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")

async def query_openrouter(system_prompt: str, user_query: str) -> str:
    """
    Улучшенный запрос к OpenRouter с обработкой ошибок и фильтрацией ответов
    """
    if not OPENROUTER_API_KEY:
        return "Ошибка конфигурации: API ключ OpenRouter не задан."

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://xn--j1aijl6bd.xn--p1ai/",
                    "X-Title": "ECOFES Bot"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    "temperature": 0.3,  # Снижаем температуру для более точных ответов
                    "max_tokens": 400,   # Ограничиваем длину ответа
                    "top_p": 0.9        # Добавляем top_p для стабильности
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                raw_answer = data["choices"][0]["message"]["content"].strip()
                
                # Фильтруем и улучшаем ответ
                filtered_answer = filter_and_improve_answer(raw_answer)
                return filtered_answer
                
            else:
                logger.error(f"OpenRouter API error {response.status_code}: {response.text}")
                return (
                    "К сожалению, временные технические проблемы с AI-системой. "
                    "Для получения консультации обратитесь к менеджеру: +7 (800) 700-80-39"
                )

        except httpx.TimeoutException:
            logger.error("OpenRouter API timeout")
            return (
                "Превышено время ожидания ответа. "
                "Попробуйте переформулировать вопрос или обратитесь к специалисту."
            )
        except Exception as e:
            logger.error(f"OpenRouter API exception: {str(e)}")
            return (
                "Возникла ошибка при обработке запроса. "
                "Рекомендую обратиться к менеджеру для персональной консультации."
            )

def filter_and_improve_answer(answer: str) -> str:
    """
    Фильтрует и улучшает ответ от LLM
    """
    # Убираем лишние символы и пробелы
    answer = answer.strip()
    
    # Проверяем, не содержит ли ответ явно некорректную информацию
    problematic_phrases = [
        "я не знаю",
        "не могу сказать",
        "не имею информации",
        "у меня нет данных",
        "к сожалению, я не",
        "извините, но я не"
    ]
    
    answer_lower = answer.lower()
    
    # Если ответ содержит признаки неуверенности, заменяем стандартным
    for phrase in problematic_phrases:
        if phrase in answer_lower:
            return (
                "В доступной мне информации нет точного ответа на ваш вопрос. "
                "Рекомендую обратиться к нашему специалисту для детальной консультации: "
                "+7 (800) 700-80-39"
            )
    
    # Ограничиваем длину ответа
    if len(answer) > 800:
        # Обрезаем по последнему предложению
        sentences = answer.split('.')
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence + ".") <= 700:
                truncated += sentence + "."
            else:
                break
        
        if truncated:
            answer = truncated + "\n\nДля получения более подробной информации обратитесь к специалисту."
        else:
            answer = answer[:700] + "...\n\nДля подробной консультации звоните: +7 (800) 700-80-39"
    
    # Добавляем призыв к действию для технических вопросов
    if any(word in answer_lower for word in ["масло", "двигатель", "вязкость", "замена"]):
        if "консультац" not in answer_lower and "специалист" not in answer_lower:
            answer += "\n\n💡 Для персонального подбора масла обратитесь к нашему специалисту!"
    
    return answer
