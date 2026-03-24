"""
Утилиты для логирования
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Директории определяем без импорта config
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"


class Logger:
    """Класс для логирования"""
    
    def __init__(self, name="MarketplaceBot"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Очистка существующих обработчиков
        self.logger.handlers.clear()
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный обработчик
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Файловый обработчик - создаем директорию если не существует
        try:
            LOGS_DIR.mkdir(exist_ok=True)
            log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            # Если не можем создать файл лога, работаем без него
            self.logger.warning(f"Не удалось создать файл лога: {e}")
        
        # Список для хранения последних сообщений для GUI
        self.recent_messages = []
        self.max_messages = 100
        
        # Callback для GUI
        self.gui_callback = None
    
    def set_gui_callback(self, callback):
        """Установка callback для GUI"""
        self.gui_callback = callback
    
    def _add_message(self, message):
        """Добавление сообщения в список"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_message = f"[{timestamp}] {message}"
        self.recent_messages.append(full_message)
        
        # Ограничение количества сообщений
        if len(self.recent_messages) > self.max_messages:
            self.recent_messages.pop(0)
        
        # Вызов callback если установлен
        if self.gui_callback:
            try:
                self.gui_callback(full_message)
            except Exception as e:
                self.logger.debug(f"GUI callback failed: {e}")
    
    def debug(self, message):
        self._add_message(message)
        self.logger.debug(message)
    
    def info(self, message):
        self._add_message(message)
        self.logger.info(message)
    
    def warning(self, message):
        self._add_message(message)
        self.logger.warning(message)
    
    def error(self, message):
        self._add_message(message)
        self.logger.error(message)
    
    def critical(self, message):
        self._add_message(message)
        self.logger.critical(message)
    
    def exception(self, message):
        self._add_message(message)
        self.logger.exception(message)
    
    def get_recent_messages(self):
        """Получение последних сообщений"""
        return self.recent_messages


# Глобальный экземпляр логера
logger = Logger()
