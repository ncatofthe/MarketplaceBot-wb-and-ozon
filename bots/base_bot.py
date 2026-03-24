"""
Базовый класс для ботов
"""
import time
import threading
from abc import ABC, abstractmethod
from utils import logger, answer_generator
from config import config


class BaseBot(ABC):
    """Абстрактный базовый класс для ботов маркетплейсов"""
    
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        
    @abstractmethod
    def connect(self):
        """Подключение к API"""
        pass
    
    @abstractmethod
    def get_unanswered_reviews(self):
        """Получение неотвеченных отзывов"""
        pass
    
    @abstractmethod
    def send_answer(self, review_id, text):
        """Отправка ответа на отзыв"""
        pass
    
    def process_reviews(self):
        """Обработка неотвеченных отзывов"""
        logger.info(f"{self.__class__.__name__}: Начало обработки отзывов")
        
        try:
            # Получение неотвеченных отзывов
            reviews = self.get_unanswered_reviews()
            
            if not reviews:
                logger.info(f"{self.__class__.__name__}: Нет новых отзывов для обработки")
                return
            
            # Получение настроек
            min_stars = config.get("general", "min_stars")
            max_answers = config.get("general", "max_answers_per_run")
            short_sleep = config.get("general", "short_sleep")
            
            answered_count = 0
            
            for review in reviews:
                # Проверка флага остановки
                if self.stop_event.is_set():
                    logger.info(f"{self.__class__.__name__}: Остановка по запросу пользователя")
                    break
                
                # Проверка лимита ответов
                if max_answers > 0 and answered_count >= max_answers:
                    logger.info(f"{self.__class__.__name__}: Достигнут лимит ответов ({max_answers})")
                    break
                
                # Получение данных отзыва
                stars = review.get("rating") or 5  # Fallback if missing
                if stars == 0:
                    stars = 5  # Assume 5 for UNPROCESSED without rating
                review_id = review.get("id") or review.get("review_id")
                has_comment = bool(review.get("comment") or review.get("text"))
                logger.debug(f"{self.__class__.__name__}: Processing review {review_id} rating={stars} has_comment={has_comment}")
                
                # Проверка минимального количества звезд
                if stars < min_stars:
                    logger.info(f"{self.__class__.__name__}: Пропуск отзыва {review_id} (звезд: {stars} < {min_stars})")
                    continue
                
                if not review_id:
                    continue
                
                # Генерация ответа
                answer_text = answer_generator.generate(stars, has_comment)
                logger.info(f"{self.__class__.__name__}: Отзыв {review_id} (Ozon rating={stars}, has_comment={has_comment}): '{answer_text[:100]}...'")
                
                # Отправка ответа
                success = self.send_answer(review_id, answer_text)
                
                if success:
                    answered_count += 1
                    logger.info(f"{self.__class__.__name__}: Ответ отправлен на отзыв {review_id} ({stars} звезд)")
                else:
                    logger.warning(f"{self.__class__.__name__}: Не удалось отправить ответ на отзыв {review_id}")
                
                # Задержка между ответами
                time.sleep(short_sleep)
            
            logger.info(f"{self.__class__.__name__}: Обработка завершена. Отвечено на {answered_count} отзывов")
            
        except Exception as e:
            logger.exception(f"{self.__class__.__name__}: Ошибка при обработке отзывов: {e}")
    
    def start(self):
        """Запуск бота в отдельном потоке"""
        if self.is_running:
            logger.warning(f"{self.__class__.__name__}: Бот уже запущен")
            return
        
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"{self.__class__.__name__}: Бот запущен")
    
    def stop(self):
        """Остановка бота"""
        if not self.is_running:
            return
        
        logger.info(f"{self.__class__.__name__}: Остановка бота...")
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=10)
        
        self.is_running = False
        logger.info(f"{self.__class__.__name__}: Бот остановлен")
    
    def _run(self):
        """Основной цикл работы бота"""
        check_interval = config.get("general", "check_interval") * 60  # минуты в секунды
        
        while not self.stop_event.is_set():
            try:
                # Подключение к API
                if not self.connect():
                    logger.error(f"{self.__class__.__name__}: Не удалось подключиться к API")
                    continue
                
                # Обработка отзывов
                self.process_reviews()
                
            except Exception as e:
                logger.exception(f"{self.__class__.__name__}: Ошибка в основном цикле: {e}")
            
            # Ожидание до следующей проверки
            if not self.stop_event.is_set():
                logger.debug(f"{self.__class__.__name__}: Ожидание {check_interval} секунд до следующей проверки")
                self.stop_event.wait(check_interval)
    
    def get_status(self):
        """Получение статуса бота"""
        return {
            "running": self.is_running,
            "class": self.__class__.__name__
        }

