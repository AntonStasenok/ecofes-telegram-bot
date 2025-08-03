# bot/services/llm_service.py
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")  # или "openai/gpt-3.5-turbo"

async def query_openrouter(system_prompt: str, user_query: str) -> str:
    if not OPENROUTER_API_KEY:
        return "Ошибка: API ключ OpenRouter не задан."

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://xn--j1aijl6bd.xn--p1ai/",  # Укажи свой сайт
                    "X-Title": "ECOFES Bot"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    "temperature": 0.5,
                    "max_tokens": 500
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"Ошибка {response.status_code}: {response.text}"

        except Exception as e:
            return f"Ошибка подключения к OpenRouter: {str(e)}"
