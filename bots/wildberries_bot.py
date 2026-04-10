"""
Бот для Wildberries
"""
import copy
from api import WBAPI
from .base_bot import BaseBot
from utils import logger
from config import config


class WildberriesBot(BaseBot):
    """Бот для автоматического ответа на отзывы Wildberries"""
    
    def __init__(self, account=None):
        super().__init__()
        self.api = None
        self.api_key = ""
        self.marketplace = "wildberries"
        self.account = None
        self.account_id = None
        self.account_name = "Wildberries"
        self.account_enabled = False
        if account is not None:
            self.set_account(account)

    def set_account(self, account):
        """Привязка бота к конкретному аккаунту."""
        self.account = copy.deepcopy(account)
        self._apply_account(self.account)

    def _apply_account(self, account):
        """Применение account metadata и секретов."""
        self.account_id = account.get("id")
        self.account_name = account.get("name") or "Wildberries"
        self.account_enabled = bool(account.get("enabled", False))
        self.api_key = account.get("api_key", "")

    def _resolve_account(self):
        """Получение account config для текущего runtime-бота."""
        if self.account is not None:
            return copy.deepcopy(self.account)

        for account in config.get_accounts():
            if account.get("marketplace") == self.marketplace:
                return copy.deepcopy(account)

        wb_config = config.get("wildberries")
        if not wb_config:
            return None

        return {
            "id": "wildberries-legacy",
            "name": "Wildberries",
            "marketplace": self.marketplace,
            "enabled": wb_config.get("enabled", False),
            "api_key": wb_config.get("api_key", ""),
            "company_id": "",
        }
    
    def connect(self) -> bool:
        """Подключение к API Wildberries"""
        try:
            account = self._resolve_account()
            if not account:
                logger.error("Wildberries: Конфигурация не найдена")
                return False

            self._apply_account(account)
            
            if not self.api_key:
                logger.error("Wildberries: API ключ не настроен")
                return False
            
            # Создание экземпляра API
            self.api = WBAPI(self.api_key)
            
            # Тестовый запрос для проверки подключения
            test_result = self.api.get_unanswered_count()
            unanswered_count = None
            if isinstance(test_result, dict):
                unanswered_count = test_result.get("countUnanswered")
            elif isinstance(test_result, int) and not isinstance(test_result, bool):
                unanswered_count = test_result

            if unanswered_count is None:
                logger.error(
                    "Wildberries: Health-check не прошел, API не вернул валидный countUnanswered"
                )
                return False
            
            logger.info(f"Wildberries: Успешное подключение к API, unanswered={unanswered_count}")
            return True
            
        except Exception as e:
            logger.exception(f"Wildberries: Ошибка при подключении к API: {e}")
            return False
    
    def get_unanswered_reviews(self):
        """Получение неотвеченных отзывов"""
        if not self.api:
            logger.error("Wildberries: API не инициализирован")
            return []
        
        try:
            feedbacks = self.api.get_unanswered_feedbacks(limit=1000)
            
            # Преобразование формата отзывов to uniform with Ozon
            formatted_feedbacks = []
            for feedback in feedbacks:
                rating = feedback.get("productValuation", 5)
                formatted_feedbacks.append({
                    "id": feedback.get("id"),
                    "review_id": feedback.get("id"),
                    "rating": rating,
                    "text": feedback.get("text", ""),
                    "comment": feedback.get("text", ""),
                    "product_id": feedback.get("nmId"),
                    "answer": feedback.get("answer", {})
                })
                logger.debug(f"WB formatted {feedback.get('id')[:8]}... rating={rating} text_len={len(feedback.get('text',''))}")
            
            logger.info(f"Wildberries: Formatted {len(formatted_feedbacks)} unanswered reviews")
            return formatted_feedbacks
            
        except Exception as e:
            logger.exception(f"Wildberries: Ошибка при получении отзывов: {e}")
            return []
    
    def send_answer(self, review_id: str, text: str) -> bool:
        """Отправка ответа на отзыв"""
        if not self.api:
            logger.error("Wildberries: API не инициализирован")
            return False
        
        try:
            return self.api.send_answer(review_id, text)
        except Exception as e:
            logger.exception(f"Wildberries: Ошибка при отправке ответа: {e}")
            return False
    
    def get_status(self):
        """Получение статуса бота"""
        if self.account_id is None:
            account = self._resolve_account()
            if account:
                self._apply_account(account)

        base_status = super().get_status()
        base_status.update({
            "name": "Wildberries",
            "marketplace": self.marketplace,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account_enabled": self.account_enabled,
            "api_key_configured": bool(self.api_key)
        })
        return base_status
