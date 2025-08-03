# inspect_chroma.py
import chromadb
from chromadb.config import Settings

# Подключаемся к той же БД, что и бот
client = chromadb.PersistentClient(path="data/chroma_db")

# Получаем коллекцию
collection = client.get_collection("ecofes_docs")

# Получаем все документы
data = collection.get(include=["documents", "metadatas", "embeddings"])

print(f"📊 Найдено документов: {len(data['ids'])}\n")

for i, (doc_id, doc, meta, emb) in enumerate(zip(
    data["ids"],
    data["documents"],
    data["metadatas"],
    data["embeddings"]
)):
    print(f"📄 [{i+1}] ID: {doc_id}")
    print(f"   📝 Текст: {doc[:300]}...")  # первые 300 символов
    print(f"   🏷️  Метаданные: {meta}")
    print(f"   🔤 Эмбеддинг: длина {len(emb)} (вывод вектора отключён)")
    print("-" * 50)
