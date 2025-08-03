# bot/services/rag_engine.py
import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List

# Загружаем модель для русского языка
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" # "intfloat/multilingual-e5-large"  # Поддерживает русский
# Альтернатива (меньше): "cointegrated/LaBSE-en-ru" или "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

class RAGEngine:
    def __init__(self, docs_path: str = "data/docs", db_path: str = "data/chroma_db"):
        self.docs_path = docs_path
        self.db_path = db_path
        self.model = SentenceTransformer(MODEL_NAME)

        # ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection("ecofes_docs")

        # Загружаем и индексируем документы при старте
        self._load_and_index_docs()

    def _load_and_index_docs(self):
        import glob
        import os

        # Проверяем, есть ли файлы
        doc_files = list(glob.glob(f"{self.docs_path}/**/*.*", recursive=True))
        print(f"🔍 Найдено файлов в {self.docs_path}: {len(doc_files)}")
        for f in doc_files:
            print(f"📄 {f}")

        # Если уже есть документы в БД — не перезагружаем
        if self.collection.count() > 0:
            print(f"✅ Коллекция уже содержит {self.collection.count()} документов. Пропускаем загрузку.")
            return

        documents = []
        metadatas = []
        ids = []

        for file_path in doc_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if len(content) < 10:
                        print(f"⚠️ Пропускаем пустой файл: {file_path}")
                        continue

                    chunks = self._split_text(content, chunk_size=300)
                    print(f"✂️  Файл {os.path.basename(file_path)} разбит на {len(chunks)} чанков")

                    for i, chunk in enumerate(chunks):
                        doc_id = f"{os.path.basename(file_path)}_{i}"
                        documents.append(chunk)
                        metadatas.append({"source": file_path})
                        ids.append(doc_id)
            except Exception as e:
                print(f"❌ Ошибка чтения {file_path}: {e}")

        if documents:
            print(f"📦 Индексируем {len(documents)} чанков в ChromaDB...")
            embeddings = self.model.encode(documents).tolist()
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            print(f"✅ Успешно проиндексировано {len(documents)} чанков")
        else:
            print("❌ НЕТ документов для индексации. Проверь папку data/docs")
    

    def _split_text(self, text: str, chunk_size: int = 300) -> List[str]:
        words = text.split()
        return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

    def search(self, query: str, n_results: int = 3) -> List[str]:
        # Генерируем эмбеддинг запроса
        query_embedding = self.model.encode([query]).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )

        return results["documents"][0] if results["documents"] else []
