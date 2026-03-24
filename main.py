#!/usr/bin/env python3
"""
Бот для автоматического ответа на отзывы на маркетплейсах Ozon и Wildberries

Основной файл приложения с графическим интерфейсом
"""
import sys
import os

# Добавление пути к проекту в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import run_gui


def main():
    """Главная функция"""
    print("Запуск бота для маркетплейсов...")
    run_gui()


if __name__ == "__main__":
    main()

