"""
WSGI entry point for production deployment
"""
from app import app
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    app.run()
