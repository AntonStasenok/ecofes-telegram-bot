# bot/services/rag_engine.py
import os
import chromadb
import requests
import base64
import uuid
import time
from typing import List
import urllib3

tr_text = 1000
chunk_size = 200
n_res = 3

# Отключаем предупреждения о непроверенном SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RAGEngine:
    def __init__(self, docs_path: str = "data/docs", db_path: str = "data/chroma_db"):
        self.docs_path = docs_path
        self.db_path = db_path

        # Переменные окружения для GigaChat
        self.GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
        self.GIGACHAT_SECRET = os.getenv("GIGACHAT_SECRET")
        if not self.GIGACHAT_CLIENT_ID or not self.GIGACHAT_SECRET:
            raise EnvironmentError("GIGACHAT_CLIENT_ID и GIGACHAT_SECRET должны быть заданы в .env")

        self.access_token = None
        self._refresh_token()

        # ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection("ecofes_docs")

        # Загружаем и индексируем документы
        self._load_and_index_docs()

    def _refresh_token(self):
        """Получает новый access_token через OAuth"""
        credentials = f"{self.GIGACHAT_CLIENT_ID}:{self.GIGACHAT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {"scope": "GIGACHAT_API_PERS"}

        try:
            response = requests.post(url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            print("✅ access_token успешно получен")
        except requests.exceptions.HTTPError as e:
            print(f"❌ Ошибка при получении токена: {e.response.status_code} {e.response.text}")
            raise

    def _get_embedding(self, text: str) -> List[float]:
        """Получает эмбеддинг через GigaChat API"""
        url = "https://gigachat.devices.sberbank.ru/api/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        # Усекаем и ограничиваем текст
        truncated_text = text[:tr_text]  # Ограничение по символам
        payload = {
            "model": "Embeddings",
            "input": [truncated_text]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            if response.status_code == 401:  # Unauthorized
                print("🔐 Токен устарел. Получаем новый...")
                self._refresh_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.post(url, headers=headers, json=payload, verify=False)

            response.raise_for_status()
            return response.json()["data"][0]["embedding"]

        except requests.exceptions.HTTPError as e:
            if response.status_code == 413:
                print(f"❌ Текст слишком длинный для GigaChat: '{text[:500]}...'")
            else:
                print(f"❌ Ошибка {response.status_code}: {response.text}")
            raise
        except Exception as e:
            print(f"❌ Неизвестная ошибка: {e}")
            raise

    def _split_text(self, text: str, chunk_size: int = chunk_size) -> List[str]:
        """Разбивает текст на чанки по количеству слов"""
        words = text.split()
        return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

    def _load_and_index_docs(self):
        import glob
        import os

        doc_files = list(glob.glob(f"{self.docs_path}/**/*.*", recursive=True))
        print(f"🔍 Найдено файлов: {len(doc_files)}")

        if self.collection.count() > 0:
            print(f"✅ Коллекция уже содержит {self.collection.count()} документов.")
            return

        documents = []
        metadatas = []
        ids = []
        debug_file = dict()

        for file_path in doc_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if len(content) < 10:
                        print(f"⚠️ Пропускаем пустой файл: {file_path}")
                        continue

                    chunks = self._split_text(content, chunk_size=chunk_size)  # Безопасный размер
                    print(f"✂️ Файл {os.path.basename(file_path)} разбит на {len(chunks)} чанков")

                    for i, chunk in enumerate(chunks):
                        doc_id = f"{os.path.basename(file_path)}_{i}"
                        # Проверка длины чанка перед добавлением
                        if len(chunk) > tr_text*2:
                            print(f"⚠️ Чанк {doc_id} слишком длинный ({len(chunk)} символов), пропускаем")
                            continue
                        documents.append(chunk)
                        metadatas.append({"source": file_path})
                        ids.append(doc_id)
                        debug_file[i] = [file_path,chunk]
            except Exception as e:
                print(f"❌ Ошибка чтения {file_path}: {e}")

        if documents:
            print(f"📦 Индексируем {len(documents)} чанков...")
            embeddings = []
            for i, doc in enumerate(documents):
                print(f"🌐 Получаем эмбеддинг {i + 1}/{len(documents)}")
                try:
                    emb = self._get_embedding(doc)
                    embeddings.append(emb)
                except Exception:
                    print(f"❌ Пропускаем чанк {i + 1} из-за ошибки")
                    continue  # Пропускаем проблемный чанк
                time.sleep(0.1)  # Анти-флуд

            if embeddings:
                self.collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
                print(f"✅ Успешно проиндексировано {len(embeddings)} чанков")
            else:
                print("❌ Не удалось получить ни одного эмбеддинга")
        else:
            print("❌ НЕТ документов для индексации.")

    def search(self, query: str, n_results: int = n_res) -> List[str]:
        """Поиск по запросу"""
        try:
            query_embedding = self._get_embedding(query)
            results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            print(f"❌ Ошибка при поиске: {e}")
            return []
