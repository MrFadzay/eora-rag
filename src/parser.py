"""
Парсер для извлечения контента с сайта EORA
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import os
from typing import Dict, List, Optional


class EoraParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def parse_case_page(self, url: str) -> Optional[Dict]:
        """Парсит одну страницу кейса"""
        try:
            print(f"Парсинг: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Извлекаем основную информацию
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            content = self._extract_content(soup)

            case_data = {
                'url': url,
                'title': title,
                'description': description,
                'content': content,
                'full_text': f"{title}\n\n{description}\n\n{content}"
            }

            print(f"✓ Успешно: {title[:50]}...")
            return case_data

        except Exception as e:
            print(f"✗ Ошибка при парсинге {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Извлекает заголовок страницы"""
        # Пробуем разные селекторы
        selectors = [
            'title',
            'h1',
            '[property="og:title"]',
            '.t-title',
            '.t030__title'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if selector == '[property="og:title"]':
                    return element.get('content', '').strip()
                else:
                    return element.get_text().strip()

        return "Без названия"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Извлекает описание"""
        selectors = [
            '[name="description"]',
            '[property="og:description"]',
            '.t-descr',
            '.t030__descr'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get('content', '').strip()

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Извлекает основной контент страницы"""
        # Удаляем ненужные элементы
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'input', 'button']):
            element.decompose()

        # Удаляем элементы с классами форм и навигации
        for element in soup.find_all(class_=lambda x: x and any(word in x.lower() for word in ['form', 'nav', 'menu', 'popup', 'modal'])):
            element.decompose()

        content_parts = []

        # Ищем заголовки и текстовые блоки
        for tag in ['h1', 'h2', 'h3', 'h4', 'p', 'div']:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text(separator=' ', strip=True)
                # Фильтруем качественный контент
                if (len(text) > 30 and
                    not any(word in text.lower() for word in ['cookie', 'email', 'телефон', 'отправить', 'обязательное поле']) and
                        not text.startswith('Пожалуйста')):
                    content_parts.append(text)

        # Убираем дубликаты и сортируем по длине
        unique_parts = list(dict.fromkeys(content_parts))  # Убираем дубликаты
        unique_parts.sort(key=len, reverse=True)  # Сортируем по длине

        return '\n\n'.join(unique_parts[:5])  # Берем 5 самых длинных блоков

    def parse_all_cases(self, urls: List[str], output_file: str = 'data/parsed_cases.json') -> List[Dict]:
        """Парсит все кейсы и сохраняет в файл"""
        cases = []

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Обрабатываем кейс...")

            case_data = self.parse_case_page(url)
            if case_data:
                cases.append(case_data)

            # Пауза между запросами
            time.sleep(1)

        # Сохраняем результат
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Сохранено {len(cases)} кейсов в {output_file}")
        return cases


def main():
    """Парсим все кейсы или тестируем на одном"""
    import sys
    from urls import EORA_CASE_URLS

    parser = EoraParser()

    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        # Парсим все кейсы
        print(f"Начинаем парсинг {len(EORA_CASE_URLS)} кейсов...")
        cases = parser.parse_all_cases(EORA_CASE_URLS)
        print(f"\n✅ Готово! Спарсено {len(cases)} кейсов")
    elif len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Тестируем на первых 3 кейсах
        test_urls = EORA_CASE_URLS[:3]
        print(f"Тестируем парсинг на {len(test_urls)} кейсах...")
        cases = parser.parse_all_cases(test_urls, 'data/test_cases.json')
        print(f"\n✅ Тест завершен! Спарсено {len(cases)} кейсов")
    else:
        # Тестируем на одном кейсе
        test_url = "https://eora.ru/cases/chat-boty/hr-bot-dlya-magnit-kotoriy-priglashaet-na-sobesedovanie"

        case = parser.parse_case_page(test_url)
        if case:
            print("\n" + "="*50)
            print("РЕЗУЛЬТАТ ПАРСИНГА:")
            print("="*50)
            print(f"URL: {case['url']}")
            print(f"Заголовок: {case['title']}")
            print(f"Описание: {case['description'][:200]}...")
            print(f"Контент: {case['content'][:300]}...")
            print("="*50)
            print("\nДля парсинга всех кейсов запустите: python src/parser.py --all")


if __name__ == "__main__":
    main()
