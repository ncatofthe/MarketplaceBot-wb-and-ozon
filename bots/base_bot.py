"""
Базовый класс для ботов
"""
import time
import threading
from datetime import datetime
from abc import ABC, abstractmethod
from utils import logger, answer_generator
from utils.review_state import review_state_store
from config import config


class BaseBot(ABC):
    """Абстрактный базовый класс для ботов маркетплейсов"""
    
    def __init__(self, review_state=None):
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.review_state = review_state if review_state is not None else review_state_store
        self.stats = {
            "running": False,
            "stopping": False,
            "found_reviews": 0,
            "processed_reviews": 0,
            "answered_reviews": 0,
            "skipped_reviews": 0,
            "error_count": 0,
            "last_error": None,
            "last_run_started_at": None,
            "last_run_finished_at": None,
            "last_success_at": None,
        }

    @staticmethod
    def _now_timestamp():
        """Текущее время для отображения в GUI."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _sync_runtime_stats(self):
        """Синхронизация runtime-флагов со статистикой."""
        thread_alive = bool(self.thread and self.thread.is_alive())
        running = bool(self.is_running or thread_alive)
        self.stats["running"] = running
        self.stats["stopping"] = bool(running and self.stop_event.is_set())

    def _start_cycle_stats(self):
        """Сброс статистики текущего цикла перед новой обработкой."""
        self.stats["found_reviews"] = 0
        self.stats["processed_reviews"] = 0
        self.stats["answered_reviews"] = 0
        self.stats["skipped_reviews"] = 0
        self.stats["error_count"] = 0
        self.stats["last_error"] = None
        self.stats["last_run_started_at"] = self._now_timestamp()
        self.stats["last_run_finished_at"] = None
        self._sync_runtime_stats()

    def _finish_cycle_stats(self, success=False):
        """Фиксация завершения цикла."""
        finished_at = self._now_timestamp()
        self.stats["last_run_finished_at"] = finished_at
        if success:
            self.stats["last_success_at"] = finished_at
        self._sync_runtime_stats()

    def _record_error(self, message):
        """Единая запись ошибок для GUI и логов."""
        self.stats["error_count"] += 1
        self.stats["last_error"] = message
        self._sync_runtime_stats()

    def _get_deduplication_context(self):
        """Контекст account-aware дедупликации для persistent state."""
        if self.review_state is None:
            return None, None

        marketplace = str(getattr(self, "marketplace", "") or "").strip().lower()
        account_id = str(getattr(self, "account_id", "") or "").strip()
        if not marketplace or not account_id:
            return None, None
        return marketplace, account_id

    def _is_duplicate_review(self, review_id):
        """Проверка, был ли отзыв уже успешно обработан для аккаунта."""
        marketplace, account_id = self._get_deduplication_context()
        if not marketplace or not account_id or not review_id:
            return False
        return self.review_state.has_processed(marketplace, account_id, review_id)

    def _mark_review_processed(self, review_id):
        """Персистентная пометка успешно обработанного отзыва."""
        marketplace, account_id = self._get_deduplication_context()
        if not marketplace or not account_id or not review_id:
            return True
        return self.review_state.mark_processed(marketplace, account_id, review_id)
    
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
            self.stats["found_reviews"] = len(reviews or [])
            
            if not reviews:
                logger.info(f"{self.__class__.__name__}: Нет новых отзывов для обработки")
                return True
            
            # Получение настроек
            min_stars = config.get("general", "min_stars")
            max_answers = config.get("general", "max_answers_per_run")
            short_sleep = config.get("general", "short_sleep")

            for review in reviews:
                # Проверка флага остановки
                if self.stop_event.is_set():
                    logger.info(f"{self.__class__.__name__}: Остановка по запросу пользователя")
                    break
                
                # Проверка лимита ответов
                if max_answers > 0 and self.stats["answered_reviews"] >= max_answers:
                    logger.info(f"{self.__class__.__name__}: Достигнут лимит ответов ({max_answers})")
                    break
                
                # Получение данных отзыва
                stars = review.get("rating") or 5  # Fallback if missing
                if stars == 0:
                    stars = 5  # Assume 5 for UNPROCESSED without rating
                review_id = review.get("id") or review.get("review_id")
                has_comment = bool(review.get("comment") or review.get("text"))
                logger.debug(f"{self.__class__.__name__}: Processing review {review_id} rating={stars} has_comment={has_comment}")

                if not review_id:
                    self.stats["processed_reviews"] += 1
                    self.stats["skipped_reviews"] += 1
                    logger.warning(f"{self.__class__.__name__}: Пропуск отзыва без идентификатора")
                    continue
                
                # Проверка минимального количества звезд
                if stars < min_stars:
                    self.stats["processed_reviews"] += 1
                    self.stats["skipped_reviews"] += 1
                    logger.info(f"{self.__class__.__name__}: Пропуск отзыва {review_id} (звезд: {stars} < {min_stars})")
                    continue

                if self._is_duplicate_review(review_id):
                    self.stats["processed_reviews"] += 1
                    self.stats["skipped_reviews"] += 1
                    logger.info(
                        f"{self.__class__.__name__}: Пропуск дубликата отзыва {review_id} "
                        f"для аккаунта {getattr(self, 'account_id', 'unknown')}"
                    )
                    continue
                
                # Генерация ответа
                answer_text = answer_generator.generate(stars, has_comment)
                logger.info(f"{self.__class__.__name__}: Отзыв {review_id} (Ozon rating={stars}, has_comment={has_comment}): '{answer_text[:100]}...'")
                
                # Отправка ответа
                success = self.send_answer(review_id, answer_text)
                self.stats["processed_reviews"] += 1
                
                if success:
                    self.stats["answered_reviews"] += 1
                    if not self._mark_review_processed(review_id):
                        error_message = (
                            f"Ответ на отзыв {review_id} отправлен, но anti-duplicate state "
                            f"не был сохранен"
                        )
                        self._record_error(error_message)
                        logger.warning(f"{self.__class__.__name__}: {error_message}")
                    logger.info(f"{self.__class__.__name__}: Ответ отправлен на отзыв {review_id} ({stars} звезд)")
                else:
                    error_message = f"Не удалось отправить ответ на отзыв {review_id}"
                    self._record_error(error_message)
                    logger.warning(f"{self.__class__.__name__}: {error_message}")
                
                # Задержка между ответами
                if self.stop_event.wait(short_sleep):
                    break
            
            logger.info(
                f"{self.__class__.__name__}: Обработка завершена. "
                f"Найдено={self.stats['found_reviews']}, обработано={self.stats['processed_reviews']}, "
                f"отвечено={self.stats['answered_reviews']}, пропущено={self.stats['skipped_reviews']}, "
                f"ошибок={self.stats['error_count']}"
            )
            return True
        except Exception as e:
            error_message = f"Ошибка при обработке отзывов: {e}"
            self._record_error(error_message)
            logger.exception(f"{self.__class__.__name__}: {error_message}")
            return False
    
    def start(self):
        """Запуск бота в отдельном потоке"""
        if self.thread and self.thread.is_alive():
            self.is_running = True
            self._sync_runtime_stats()
            logger.warning(f"{self.__class__.__name__}: Бот уже запущен")
            return False
        
        self.stop_event.clear()
        self.is_running = True
        self._sync_runtime_stats()
        self.thread = threading.Thread(
            target=self._run,
            name=f"{self.__class__.__name__}Thread",
            daemon=True,
        )
        self.thread.start()
        
        logger.info(f"{self.__class__.__name__}: Бот запущен")
        return True
    
    def stop(self):
        """Остановка бота"""
        thread_alive = bool(self.thread and self.thread.is_alive())
        if not thread_alive:
            self.is_running = False
            self._sync_runtime_stats()
            logger.info(f"{self.__class__.__name__}: Бот уже остановлен")
            return True
        
        logger.info(f"{self.__class__.__name__}: Остановка бота...")
        self.stop_event.set()
        self._sync_runtime_stats()
        
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            self.is_running = True
            self._record_error("Поток не завершился за 10 секунд")
            logger.warning(
                f"{self.__class__.__name__}: Поток не завершился за 10 секунд, бот еще останавливается"
            )
            return False

        self.is_running = False
        self._sync_runtime_stats()
        logger.info(f"{self.__class__.__name__}: Бот остановлен")
        return True
    
    def _run(self):
        """Основной цикл работы бота"""
        check_interval = config.get("general", "check_interval") * 60  # минуты в секунды
        retry_delay = max(5, min(check_interval, 60))

        try:
            while not self.stop_event.is_set():
                next_delay = check_interval
                cycle_success = False
                self._start_cycle_stats()
                try:
                    # Подключение к API
                    if not self.connect():
                        error_message = "Не удалось подключиться к API"
                        self._record_error(error_message)
                        logger.error(f"{self.__class__.__name__}: {error_message}")
                        next_delay = retry_delay
                        if not self.stop_event.is_set():
                            logger.warning(
                                f"{self.__class__.__name__}: Повторная попытка подключения через {retry_delay} секунд"
                            )
                    else:
                        # Обработка отзывов
                        cycle_success = self.process_reviews() and self.stats["error_count"] == 0
                    
                except Exception as e:
                    error_message = f"Ошибка в основном цикле: {e}"
                    self._record_error(error_message)
                    next_delay = retry_delay
                    logger.exception(f"{self.__class__.__name__}: {error_message}")
                finally:
                    self._finish_cycle_stats(success=cycle_success)
                
                # Ожидание до следующей проверки
                if not self.stop_event.is_set():
                    logger.debug(f"{self.__class__.__name__}: Ожидание {next_delay} секунд до следующей проверки")
                    self.stop_event.wait(next_delay)
        finally:
            self.is_running = False
            self._sync_runtime_stats()
    
    def get_status(self):
        """Получение статуса бота"""
        self._sync_runtime_stats()
        status = dict(self.stats)
        status["class"] = self.__class__.__name__
        return status

