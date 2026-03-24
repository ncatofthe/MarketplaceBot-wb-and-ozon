"""
Генератор ответов на отзывы
"""
import random
from config import config


class AnswerGenerator:
    """Класс для генерации ответов на отзывы"""
    
    def __init__(self):
        self.templates = config.get_answer_templates()
    
    def _get_random(self, key):
        """Безопасное получение случайного элемента из шаблона"""
        template = self.templates.get(key)
        if template and isinstance(template, list) and len(template) > 0:
            return random.choice(template)
        return None
    
    def generate(self, stars, has_comment=True):
        """
        Генерация ответа на отзыв
        
        Args:
            stars: количество звезд (0-5)
            has_comment: есть ли комментарий к отзыву
        
        Returns:
            str: сгенерированный ответ
        """
        parts = []
        
        # Приветствие (50% шанс)
        greeting = self._get_random('greetings')
        if greeting and random.random() < 0.5:
            parts.append(greeting)
        
        # Основная часть в зависимости от оценки
        if stars == 5:
            # 5 звезд - благодарность
            text = self._get_random('5')
            if text:
                parts.append(text)
            
            if has_comment:
                text = self._get_random('gratitude')
            else:
                text = self._get_random('gratitude_no_comment')
            if text:
                parts.append(text)
                
        elif stars == 4:
            # 4 звезды - благодарность
            text = self._get_random('4')
            if text:
                parts.append(text)
            
            if has_comment:
                text = self._get_random('gratitude')
            else:
                text = self._get_random('gratitude_no_comment')
            if text:
                parts.append(text)
                
        elif stars == 3:
            # 3 звезды - извинения + благодарность
            if has_comment:
                text = self._get_random('3')
            else:
                text = self._get_random('3_no_comment')
            if text:
                parts.append(text)
            
            # Всегда добавляем извинения для 3 звезд
            text = self._get_random('apologies')
            if text:
                parts.append(text)
                
        elif stars == 2:
            # 2 звезды - извинения
            text = self._get_random('2')
            if text:
                parts.append(text)
            text = self._get_random('apologies')
            if text:
                parts.append(text)
            text = self._get_random('examination')
            if text:
                parts.append(text)
                
        elif stars == 1:
            # 1 звезда - извинения
            text = self._get_random('1')
            if text:
                parts.append(text)
            text = self._get_random('apologies')
            if text:
                parts.append(text)
            text = self._get_random('examination')
            if text:
                parts.append(text)
                
        elif stars == 0:
            # 0 звезд - извинения
            text = self._get_random('0')
            if text:
                parts.append(text)
            text = self._get_random('apologies')
            if text:
                parts.append(text)
            text = self._get_random('examination')
            if text:
                parts.append(text)
        
        # Основная часть (приглашение оставаться клиентом)
        if random.random() < 0.3:
            text = self._get_random('main')
            if text:
                parts.append(text)
        
        # Рекомендации (30% шанс)
        if random.random() < 0.3:
            text = self._get_random('recommendations')
            if text:
                parts.append(text)
        
        # Прощание
        text = self._get_random('goodbye')
        if text:
            parts.append(text)
        
        return " ".join(parts)
    
    def update_templates(self, templates):
        """Обновление шаблонов"""
        self.templates = templates


# Глобальный экземпляр генератора
answer_generator = AnswerGenerator()

