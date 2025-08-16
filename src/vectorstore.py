"""
Векторная база данных для хранения и поиска кейсов EORA
"""
import chromadb
import json
import os
from typing import List, Dict, Optional
import google.generativeai as genai
import numpy as np


class EoraVectorStore:
    def __init__(self, api_key: str, collection_name: str = "eora_cases"):
        """Инициализация векторной БД и Gemini клиента"""
        # Настройка Gemini
        genai.configure(api_key=api_key)

        # Настройка ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="/app/data/chroma_db")
        self.collection_name = collection_name
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "EORA cases embeddings"}
        )
        
        # Автоматическая загрузка данных при первом запуске
        if self.collection.count() == 0:
            print("База данных пустая, загружаем данные...")
            try:
                self.add_cases('/app/data/parsed_cases.json')
            except Exception as e:
                print(f"Ошибка при загрузке данных: {e}")
                # Пробуем тестовые данные как fallback
                try:
                    self.add_cases('/app/data/test_cases.json')
                except Exception as e2:
                    print(f"Ошибка при загрузке тестовых данных: {e2}")

    def reset_collection(self):
        """Очищает коллекцию для переиндексации"""
        try:
            self.chroma_client.delete_collection(name=self.collection_name)
            print(f"✓ Коллекция {self.collection_name} удалена")
        except:
            print(f"Коллекция {self.collection_name} не существует")

        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"description": "EORA cases embeddings"}
        )
        print(f"✓ Создана новая коллекция {self.collection_name}")

    def _get_embedding(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """Получает embedding для текста через Gemini API"""
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type=task_type
            )
            embedding = result['embedding']

            # Нормализация для размерности 768
            embedding_np = np.array(embedding)
            normalized_embedding = embedding_np / np.linalg.norm(embedding_np)

            return normalized_embedding.tolist()
        except Exception as e:
            print(f"Ошибка при получении embedding: {e}")
            return None

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Разбивает текст на чанки с перекрытием"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Ищем ближайший конец предложения
            if end < len(text):
                # Ищем точку, восклицательный или вопросительный знак
                for i in range(end, max(start + chunk_size//2, end - 100), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap
            if start >= len(text):
                break

        return chunks

    def add_cases(self, cases_file: str) -> int:
        """Добавляет кейсы в векторную БД"""
        print(f"Загружаем кейсы из {cases_file}...")

        with open(cases_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)

        documents = []
        embeddings = []
        metadatas = []
        ids = []

        chunk_id = 0

        for case in cases:
            print(f"Обрабатываем: {case['title'][:50]}...")

            # Разбиваем контент на чанки
            full_text = case['full_text']
            chunks = self._chunk_text(full_text)

            for i, chunk in enumerate(chunks):
                # Получаем embedding
                embedding = self._get_embedding(chunk, "retrieval_document")
                if embedding is None:
                    continue

                # Подготавливаем данные
                documents.append(chunk)
                embeddings.append(embedding)
                metadatas.append({
                    'url': case['url'],
                    'title': case['title'],
                    'description': case['description'],
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                })
                ids.append(f"case_{len(documents)}_{chunk_id}")
                chunk_id += 1

        # Добавляем в ChromaDB
        print(f"Добавляем {len(documents)} чанков в векторную БД...")
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ Добавлено {len(documents)} чанков из {len(cases)} кейсов")
        return len(documents)

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Поиск релевантных чанков по запросу"""
        print(f"Поиск по запросу: {query}")

        # Получаем embedding для запроса
        query_embedding = self._get_embedding(query, "retrieval_query")
        if query_embedding is None:
            return []

        # Поиск в ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )

        # Форматируем результаты
        search_results = []
        for i in range(len(results['documents'][0])):
            search_results.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                # Конвертируем distance в similarity
                'similarity': 1 - results['distances'][0][i]
            })

        print(f"Найдено {len(search_results)} релевантных чанков")
        return search_results

    def get_stats(self) -> Dict:
        """Получает статистику по базе данных"""
        count = self.collection.count()
        return {
            'total_chunks': count,
            'collection_name': self.collection.name
        }


def main():
    """Тестируем векторную БД"""
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ Не найден GEMINI_API_KEY в .env файле")
        return

    # Создаем векторную БД
    vectorstore = EoraVectorStore(api_key)

    if len(sys.argv) > 1 and sys.argv[1] == '--index':
        # Индексируем тестовые кейсы
        vectorstore.add_cases('data/test_cases.json')
    elif len(sys.argv) > 1 and sys.argv[1] == '--reindex':
        # Переиндексируем с полными данными
        print("Переиндексация с полными данными...")
        vectorstore.reset_collection()
        vectorstore.add_cases('data/parsed_cases.json')
    else:
        # Тестируем поиск
        results = vectorstore.search("Что вы можете сделать для ритейлеров?")

        print("\n" + "="*50)
        print("РЕЗУЛЬТАТЫ ПОИСКА:")
        print("="*50)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. Similarity: {result['similarity']:.3f}")
            print(f"Кейс: {result['metadata']['title']}")
            print(f"URL: {result['metadata']['url']}")
            print(f"Контент: {result['content'][:200]}...")
            print("-" * 50)


if __name__ == "__main__":
    main()
