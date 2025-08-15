"""
Основная логика RAG системы для EORA
"""
import os
import time
from typing import List, Dict, Tuple
import google.generativeai as genai
from vectorstore import EoraVectorStore


class EoraRAGService:
    def __init__(self, api_key: str):
        """Инициализация RAG сервиса"""
        self.vectorstore = EoraVectorStore(api_key)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        # Память сессий: session_id -> список сообщений
        self.sessions = {}

    def _build_context(self, search_results: List[Dict]) -> str:
        """Строит контекст из результатов поиска"""
        context_parts = []

        for i, result in enumerate(search_results, 1):
            metadata = result['metadata']
            content = result['content']

            context_part = f"""
Источник {i}:
Название: {metadata['title']}
URL: {metadata['url']}
Описание: {metadata['description']}
Контент: {content}
"""
            context_parts.append(context_part)

        return "\n".join(context_parts)

    def _build_prompt(self, question: str, context: str, is_first_message: bool = False, chat_history: str = "") -> str:
        """Строит промпт для генерации ответа"""
        greeting_instruction = "Поприветствуй клиента в первом сообщении" if is_first_message else "Не здоровайся повторно"

        history_context = f"\nИСТОРИЯ РАЗГОВОРА:\n{chat_history}\n" if chat_history else ""

        prompt = f"""Ты - ассистент компании EORA, которая занимается разработкой решений на основе искусственного интеллекта.

КОНТЕКСТ (информация о проектах EORA):
{context}{history_context}

ТЕКУЩИЙ ВОПРОС КЛИЕНТА: {question}

ИНСТРУКЦИИ:
1. {greeting_instruction}
2. Будь краток и конкретен - 2-3 абзаца максимум
3. Используй информацию из контекста и учитывай историю разговора
4. Приводи конкретные примеры проектов
5. Если нет релевантной информации, честно скажи об этом
6. Отвечай естественно и дружелюбно
7. Отвечай на русском языке

ОТВЕТ:"""

        return prompt

    def _get_session_history(self, session_id: str, max_messages: int = 4) -> str:
        """Получает историю сессии в виде строки"""
        if session_id not in self.sessions:
            return ""

        # Последние N сообщений
        messages = self.sessions[session_id][-max_messages:]
        history_parts = []

        for msg in messages:
            history_parts.append(f"Клиент: {msg['question']}")
            # Сокращаем ответы
            history_parts.append(f"Ассистент: {msg['answer'][:200]}...")

        return "\n".join(history_parts)

    def _save_to_session(self, session_id: str, question: str, answer: str):
        """Сохраняет сообщение в сессию"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({
            'question': question,
            'answer': answer,
            'timestamp': time.time()
        })

        # Ограничиваем размер сессии (последние 10 сообщений)
        if len(self.sessions[session_id]) > 10:
            self.sessions[session_id] = self.sessions[session_id][-10:]

    def _extract_sources(self, search_results: List[Dict]) -> List[Dict]:
        """Извлекает источники для ответа"""
        sources = []
        seen_urls = set()

        for result in search_results:
            metadata = result['metadata']
            url = metadata['url']

            if url not in seen_urls:
                sources.append({
                    'title': metadata['title'],
                    'url': url,
                    'description': metadata['description']
                })
                seen_urls.add(url)

        return sources

    def get_answer(self, question: str, session_id: str = "default", max_sources: int = 5) -> Tuple[str, List[Dict]]:
        """Получает ответ на вопрос с источниками"""
        try:
            # 1. Поиск релевантных документов
            search_results = self.vectorstore.search(
                question, n_results=max_sources)

            if not search_results:
                answer = "Извините, я не нашел релевантной информации для ответа на ваш вопрос."
                self._save_to_session(session_id, question, answer)
                return answer, []

            # 2. Построение контекста
            context = self._build_context(search_results)

            # 3. Определяем, первое ли это сообщение в сессии
            is_first_message = session_id not in self.sessions or len(
                self.sessions[session_id]) == 0

            # 4. Получаем историю разговора
            chat_history = self._get_session_history(session_id)

            # 5. Генерация ответа
            prompt = self._build_prompt(
                question, context, is_first_message, chat_history)

            response = self.model.generate_content(prompt)
            answer = response.text.strip()

            # 6. Сохраняем в сессию
            self._save_to_session(session_id, question, answer)

            # 7. Извлечение источников
            sources = self._extract_sources(search_results)

            return answer, sources

        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")
            error_answer = f"Произошла ошибка при обработке вашего запроса: {str(e)}"
            self._save_to_session(session_id, question, error_answer)
            return error_answer, []

    def get_stats(self) -> Dict:
        """Получает статистику системы"""
        return self.vectorstore.get_stats()


def main():
    """Тестируем RAG сервис"""
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ Не найден GEMINI_API_KEY в .env файле")
        return

    # Создаем RAG сервис
    rag = EoraRAGService(api_key)

    # Тестовые вопросы
    questions = [
        "Что вы можете сделать для ритейлеров?",
        "Какие у вас есть решения для HR?",
        "Работали ли вы с компьютерным зрением?",
        "Что вы делали для промышленной безопасности?"
    ]

    for question in questions:
        print(f"\n{'='*60}")
        print(f"ВОПРОС: {question}")
        print('='*60)

        answer, sources = rag.get_answer(question)

        print(f"ОТВЕТ: {answer}")

        if sources:
            print(f"\nИСТОЧНИКИ:")
            for i, source in enumerate(sources, 1):
                print(f"[{i}] {source['title']}")
                print(f"    {source['url']}")

        print("\n" + "-"*60)


if __name__ == "__main__":
    main()
