"""
Боты для маркетплейсов
"""
from .base_bot import BaseBot
from .bot_manager import BotManager
from .ozon_bot import OzonBot
from .wildberries_bot import WildberriesBot

__all__ = ['BaseBot', 'BotManager', 'OzonBot', 'WildberriesBot']

