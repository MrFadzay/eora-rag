"""
Flask веб-приложение для EORA RAG системы
"""
import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from rag_service import EoraRAGService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# Инициализируем RAG сервис
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY не найден в .env файле")

rag_service = EoraRAGService(api_key)


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """API endpoint для вопросов"""
    try:
        data = request.get_json()

        if not data or 'question' not in data:
            return jsonify({
                'error': 'Вопрос не предоставлен'
            }), 400

        question = data['question'].strip()

        # Валидация длины вопроса
        if not question:
            return jsonify({
                'error': 'Вопрос не может быть пустым'
            }), 400

        if len(question) > 1000:
            return jsonify({
                'error': 'Вопрос слишком длинный (максимум 1000 символов)'
            }), 400

        # Получаем session_id (можно передать в запросе или использовать IP)
        session_id = data.get('session_id', request.remote_addr or 'default')

        # Логируем запрос
        logger.info(f"Question from {session_id}: {question[:100]}...")

        # Получаем ответ от RAG системы
        answer, sources = rag_service.get_answer(question, session_id)

        # Логируем успешный ответ
        logger.info(
            f"Answer generated for {session_id}, sources: {len(sources)}")

        return jsonify({
            'question': question,
            'answer': answer,
            'sources': sources,
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'error': 'Произошла внутренняя ошибка сервера'
        }), 500


@app.route('/api/health')
def health_check():
    """Проверка работоспособности"""
    try:
        stats = rag_service.get_stats()
        return jsonify({
            'status': 'healthy',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """Статистика базы знаний"""
    try:
        stats = rag_service.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
