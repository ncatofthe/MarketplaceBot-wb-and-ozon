#!/usr/bin/env python3
"""
Бот для автоматического ответа на отзывы на маркетплейсах Ozon и Wildberries

Основной файл приложения с графическим интерфейсом
"""
import sys
import os
import tkinter as tk
from tkinter import messagebox

# Добавление пути к проекту в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from single_instance import SingleInstanceLock


APP_LOCK = SingleInstanceLock()


def _show_already_running_message():
    """Понятное сообщение для пользователя при втором запуске."""
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "MarketplaceBot уже запущен",
            "MarketplaceBot уже запущен.\n\nЗакройте существующий экземпляр и попробуйте снова.",
        )
        root.destroy()
    except Exception:
        print(
            "MarketplaceBot уже запущен. Закройте существующий экземпляр и попробуйте снова.",
            file=sys.stderr,
        )


def main():
    """Главная функция"""
    if not APP_LOCK.acquire():
        _show_already_running_message()
        return 1

    print("Запуск бота для маркетплейсов...")
    try:
        from gui import run_gui

        run_gui()
        return 0
    finally:
        APP_LOCK.release()


if __name__ == "__main__":
    raise SystemExit(main())

