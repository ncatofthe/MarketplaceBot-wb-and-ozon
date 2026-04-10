"""
Менеджер runtime-ботов по account_id.
"""
import copy
from config import config
from .ozon_bot import OzonBot
from .wildberries_bot import WildberriesBot


class BotManager:
    """Небольшой менеджер ботов, привязанных к конкретным аккаунтам."""

    BOT_CLASSES = {
        "ozon": OzonBot,
        "wildberries": WildberriesBot,
    }

    def __init__(self, config_manager=None):
        self.config = config_manager or config
        self.bots = {}

    @staticmethod
    def _validate_account(account):
        """Базовая валидация account-конфига для runtime."""
        if not isinstance(account, dict):
            raise ValueError("Account config must be a dict")

        account_id = str(account.get("id") or "")
        marketplace = account.get("marketplace")

        if not account_id:
            raise ValueError("Account id is required")
        if marketplace not in BotManager.BOT_CLASSES:
            raise ValueError(f"Unsupported marketplace: {marketplace}")

        return account_id, marketplace

    def _get_account_by_id(self, account_id):
        """Поиск аккаунта по id в текущем config."""
        for account in self.config.get_accounts():
            if account.get("id") == account_id:
                return copy.deepcopy(account)
        return None

    def _build_idle_status(self, account):
        """Статус аккаунта, для которого runtime-бот еще не создавался."""
        return {
            "running": False,
            "stopping": False,
            "account_id": account.get("id"),
            "account_name": account.get("name"),
            "marketplace": account.get("marketplace"),
            "account_enabled": bool(account.get("enabled", False)),
        }

    def create_bot(self, account):
        """Создание runtime-бота для конкретного аккаунта."""
        account_id, marketplace = self._validate_account(account)

        if account_id in self.bots:
            raise ValueError(f"Bot for account '{account_id}' already exists")

        bot_class = self.BOT_CLASSES[marketplace]
        bot = bot_class(account=copy.deepcopy(account))
        self.bots[account_id] = bot
        return bot

    def _ensure_bot(self, account):
        """Получение существующего бота или создание нового."""
        account_id, _ = self._validate_account(account)
        bot = self.bots.get(account_id)
        if bot is None:
            return self.create_bot(account)

        if hasattr(bot, "set_account"):
            bot.set_account(account)
        return bot

    def start_account(self, account_id):
        """Запуск конкретного аккаунта по его id."""
        account = self._get_account_by_id(account_id)
        if account is None:
            raise ValueError(f"Account '{account_id}' not found")

        bot = self._ensure_bot(account)
        return bot.start()

    def stop_account(self, account_id):
        """Остановка конкретного аккаунта по его id."""
        bot = self.bots.get(account_id)
        if bot is None:
            return True
        return bot.stop()

    def start_all_enabled(self):
        """Запуск всех включенных аккаунтов из config."""
        results = {}
        for account in self.config.get_accounts():
            if account.get("enabled"):
                results[account["id"]] = self.start_account(account["id"])
        return results

    def stop_all(self):
        """Остановка всех созданных runtime-ботов."""
        results = {}
        for account_id, bot in list(self.bots.items()):
            results[account_id] = bot.stop()
        return results

    def get_statuses(self):
        """Статусы по всем аккаунтам из config и уже созданным runtime-ботам."""
        statuses = {}
        accounts = {
            account["id"]: copy.deepcopy(account)
            for account in self.config.get_accounts()
            if account.get("id")
        }

        for account_id, account in accounts.items():
            bot = self.bots.get(account_id)
            statuses[account_id] = bot.get_status() if bot is not None else self._build_idle_status(account)

        for account_id, bot in self.bots.items():
            if account_id not in statuses:
                statuses[account_id] = bot.get_status()

        return statuses
