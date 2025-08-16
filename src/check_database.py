"""
Скрипт для проверки статуса векторной базы данных
"""
import os
from dotenv import load_dotenv
from vectorstore import EoraVectorStore


def main():
    """Проверяем статус базы данных"""
    # Загружаем переменные окружения
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ Ошибка: Не найден GEMINI_API_KEY в .env файле")
        return

    try:
        # Создаем экземпляр векторной БД
        vectorstore = EoraVectorStore(api_key)

        # Получаем статистику
        stats = vectorstore.get_stats()

        print("="*50)
        print("📊 СТАТУС ВЕКТОРНОЙ БАЗЫ ДАННЫХ")
        print("="*50)
        print(f"📊 Всего чанков: {stats['total_chunks']}")
        print(f"📊 Коллекция: {stats['collection_name']}")

        if stats['total_chunks'] == 0:
            print("\n⚠️  База данных пустая!")
            print("Для заполнения используйте:")
            print("  python seed_database.py")
        else:
            print(f"\n✅ База данных готова к работе")

        print("="*50)

    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")


if __name__ == "__main__":
    main()
