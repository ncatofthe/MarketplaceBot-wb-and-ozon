"""
Бот для Ozon
"""
from api import OzonAPI
from .base_bot import BaseBot
from utils import logger
from config import config


class OzonBot(BaseBot):
    """Бот для автоматического ответа на отзывы Ozon"""
    
    def __init__(self):
        super().__init__()
        self.api = None
        self.api_key = ""
        self.company_id = ""
    
    def connect(self) -> bool:
        """Подключение к API Ozon"""
        try:
            # Получение настроек из конфигурации
            ozon_config = config.get("ozon")
            
            if not ozon_config:
                logger.error("Ozon: Конфигурация не найдена")
                return False
            
            self.api_key = ozon_config.get("api_key", "")
            self.company_id = ozon_config.get("company_id", "")
            
            if not self.api_key or not self.company_id:
                logger.error("Ozon: API ключ или Company ID не настроены")
                return False
            
            # Создание экземпляра API
            self.api = OzonAPI(self.api_key, self.company_id)
            
            # Тестовый запрос для проверки подключения
            test_result = self.api.get_review_count()
            if "error" in test_result:
                logger.error("Ozon: Не удалось выполнить тестовый запрос к API")
                return False
            
            logger.info("Ozon: Успешное подключение к API")
            return True
            
        except Exception as e:
            logger.exception(f"Ozon: Ошибка при подключении к API: {e}")
            return False
    
    def get_unanswered_reviews(self):
        """Получение неотвеченных отзывов"""
        if not self.api:
            logger.error("Ozon: API не инициализирован")
            return []
        
        try:
            # Получение всех отзывов за последние 30 дней
            since_days = 30
            reviews = self.api.get_unanswered_reviews(since_days=since_days)
            logger.info(f"Ozon: Found {len(reviews)} unanswered reviews ready for processing")
            if reviews:
                logger.info(f"Ozon: First review example: rating={reviews[0].get('rating', 'N/A')} text_len={len(reviews[0].get('text', ''))}")
            
            # Преобразование формата отзывов
            formatted_reviews = []
            for review in reviews:
                formatted_reviews.append({
                    "id": review.get("id"),
                    "review_id": review.get("id"),
                    "rating": review.get("rating", 0),
                    "text": review.get("text", ""),
                    "comment": review.get("text", ""),
                    "answer": review.get("answer")
                })
            
            return formatted_reviews
            
        except Exception as e:
            logger.exception(f"Ozon: Ошибка при получении отзывов: {e}")
            return []
    
    def send_answer(self, review_id: str, text: str) -> bool:
        """Отправка ответа на отзыв"""
        if not self.api:
            logger.error("Ozon: API не инициализирован")
            return False
        
        try:
            return self.api.send_answer(review_id, text)
        except Exception as e:
            logger.exception(f"Ozon: Ошибка при отправке ответа: {e}")
            return False
    
    def get_status(self):
        """Получение статуса бота"""
        base_status = super().get_status()
        base_status.update({
            "name": "Ozon",
            "api_key_configured": bool(self.api_key),
            "company_id_configured": bool(self.company_id)
        })
        return base_status

