"""
Скрипт для заполнения векторной базы данных кейсами EORA
Использование:
    python seed_database.py                    # Загрузка основных данных
    python seed_database.py --test            # Загрузка тестовых данных
    python seed_database.py --reset           # Очистка и переиндексация
    python seed_database.py --yes             # Автоматическое подтверждение
                                               # для неинтерактивного режима
"""
import os
import sys
import argparse
from dotenv import load_dotenv
from vectorstore import EoraVectorStore


def get_data_path():
    """Возвращает путь к данным, основываясь на переменной окружения или пути по умолчанию."""
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'data'
    )
    return os.getenv('DATA_PATH', default_path)


def main():
    """Основная функция для заполнения базы данных"""
    parser = argparse.ArgumentParser(
        description='Заполнение векторной базы данных кейсами EORA')
    parser.add_argument('--test', action='store_true',
                        help='Использовать тестовые данные вместо полных')
    parser.add_argument('--reset', action='store_true',
                        help='Очистить базу данных перед загрузкой')
    parser.add_argument('--data-file', type=str,
                        help='Путь к файлу с данными (переопределяет --test)')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Автоматически ответить "да" на все запросы')

    args = parser.parse_args()

    # Загружаем переменные окружения
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ Ошибка: Не найден GEMINI_API_KEY в .env файле")
        print("Убедитесь, что файл .env содержит строку:")
        print("GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)

    # Определяем файл с данными
    data_dir = get_data_path()
    if args.data_file:
        data_file = args.data_file
    elif args.test:
        data_file = os.path.join(data_dir, 'test_cases.json')
    else:
        data_file = os.path.join(data_dir, 'parsed_cases.json')

    # Проверяем существование файла
    if not os.path.exists(data_file):
        print(f"❌ Ошибка: Файл {data_file} не найден")
        sys.exit(1)

    print(f"🚀 Инициализация векторной базы данных...")
    print(f"📁 Файл данных: {data_file}")

    try:
        # Создаем экземпляр векторной БД
        vectorstore = EoraVectorStore(api_key)

        # Получаем статистику до загрузки
        stats_before = vectorstore.get_stats()
        print(
            f"📊 Текущее количество чанков в БД: {stats_before['total_chunks']}")

        # Очищаем базу если нужно
        if args.reset:
            print("🗑️  Очищаем базу данных...")
            vectorstore.reset_collection()

        # Проверяем, нужна ли загрузка
        if not args.reset and stats_before['total_chunks'] > 0:
            if not args.yes:
                response = input(f"База данных уже содержит {stats_before['total_chunks']} чанков. "
                                 "Продолжить загрузку? (y/N): ")
                if response.lower() not in ['y', 'yes', 'да']:
                    print("❌ Загрузка отменена")
                    sys.exit(0)
            else:
                print("✅ Флаг --yes установлен. Продолжаем загрузку автоматически.")

        # Загружаем данные
        print(f"📥 Загружаем данные из {data_file}...")
        chunks_added = vectorstore.add_cases(data_file)

        # Получаем финальную статистику
        stats_after = vectorstore.get_stats()

        print("\n" + "="*50)
        print("✅ ЗАГРУЗКА ЗАВЕРШЕНА")
        print("="*50)
        print(f"📊 Добавлено чанков: {chunks_added}")
        print(f"📊 Всего чанков в БД: {stats_after['total_chunks']}")
        print(f"📊 Коллекция: {stats_after['collection_name']}")
        print("="*50)

    except FileNotFoundError as e:
        print(f"❌ Ошибка: Файл не найден - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
