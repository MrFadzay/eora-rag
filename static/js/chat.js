// Основная логика чата
let isLoading = false;
let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    loadStats();

    // Обработка Enter в textarea
    document.getElementById('questionInput').addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });
});

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        if (response.ok) {
            document.getElementById('statsText').textContent =
                `База знаний: ${stats.total_chunks} фрагментов из кейсов EORA`;
        } else {
            document.getElementById('statsText').textContent = 'Статистика недоступна';
        }
    } catch (error) {
        document.getElementById('statsText').textContent = 'Ошибка загрузки статистики';
    }
}

// Отправка вопроса
async function sendQuestion() {
    if (isLoading) return;

    const input = document.getElementById('questionInput');
    const question = input.value.trim();

    if (!question) {
        alert('Пожалуйста, введите вопрос');
        return;
    }

    // Добавляем сообщение пользователя
    addMessage(question, 'user');

    // Очищаем поле ввода
    input.value = '';

    // Показываем индикатор загрузки
    setLoading(true);

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });

        const data = await response.json();

        if (response.ok) {
            addMessage(data.answer, 'bot', data.sources);
        } else {
            addMessage(`Ошибка: ${data.error}`, 'bot', null, true);
        }
    } catch (error) {
        addMessage(`Произошла ошибка при отправке запроса: ${error.message}`, 'bot', null, true);
    } finally {
        setLoading(false);
    }
}

// Добавление сообщения в чат
function addMessage(content, sender, sources = null, isError = false) {
    const messagesContainer = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const messageContent = document.createElement('div');
    messageContent.className = `message-content ${isError ? 'error-message' : ''}`;

    // Добавляем основной текст
    const textP = document.createElement('p');
    textP.textContent = content;
    messageContent.appendChild(textP);

    // Добавляем источники, если есть
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';

        const sourcesTitle = document.createElement('h4');
        sourcesTitle.textContent = 'Источники:';
        sourcesDiv.appendChild(sourcesTitle);

        sources.forEach((source, index) => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';

            const sourceLink = document.createElement('a');
            sourceLink.href = source.url;
            sourceLink.target = '_blank';
            sourceLink.textContent = `[${index + 1}] ${source.title}`;

            sourceItem.appendChild(sourceLink);
            sourcesDiv.appendChild(sourceItem);
        });

        messageContent.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(messageContent);
    messagesContainer.appendChild(messageDiv);

    // Прокручиваем к последнему сообщению
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Управление состоянием загрузки
function setLoading(loading) {
    isLoading = loading;
    const sendButton = document.getElementById('sendButton');
    const sendText = document.getElementById('sendText');
    const loadingText = document.getElementById('loadingText');

    if (loading) {
        sendButton.disabled = true;
        sendText.style.display = 'none';
        loadingText.style.display = 'inline';
    } else {
        sendButton.disabled = false;
        sendText.style.display = 'inline';
        loadingText.style.display = 'none';
    }
}

// Примеры вопросов (можно добавить кнопки)
const exampleQuestions = [
    "Что вы можете сделать для ритейлеров?",
    "Какие у вас есть решения для HR?",
    "Работали ли вы с компьютерным зрением?",
    "Что вы делали для промышленной безопасности?"
];

// Функция для быстрой вставки примера вопроса
function insertExampleQuestion(question) {
    document.getElementById('questionInput').value = question;
}