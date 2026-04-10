import importlib
import sys
import types
import unittest
from unittest import mock

fake_api_module = types.ModuleType("api")
fake_api_module.OzonAPI = type("ImportedOzonAPI", (), {})
fake_api_module.WBAPI = type("ImportedWBAPI", (), {})
previous_api_module = sys.modules.get("api")
sys.modules["api"] = fake_api_module
try:
    bot_manager_module = importlib.import_module("bots.bot_manager")
    ozon_bot_module = importlib.import_module("bots.ozon_bot")
    wildberries_bot_module = importlib.import_module("bots.wildberries_bot")
finally:
    if previous_api_module is None:
        del sys.modules["api"]
    else:
        sys.modules["api"] = previous_api_module


class MarketplaceBotAccountBindingTests(unittest.TestCase):
    def test_ozon_bot_uses_passed_account_instead_of_global_config(self):
        account = {
            "id": "ozon-main",
            "name": "Ozon Main",
            "marketplace": "ozon",
            "enabled": True,
            "api_key": "passed-ozon-key",
            "company_id": "passed-company",
        }
        api_client = mock.Mock()
        api_client.get_review_count.return_value = {}

        with mock.patch.object(ozon_bot_module, "OzonAPI", return_value=api_client) as api_ctor, \
             mock.patch.object(ozon_bot_module.config, "get_accounts") as get_accounts, \
             mock.patch.object(ozon_bot_module.config, "get") as legacy_get:
            bot = ozon_bot_module.OzonBot(account=account)
            result = bot.connect()

        self.assertTrue(result)
        self.assertEqual(bot.api_key, "passed-ozon-key")
        self.assertEqual(bot.company_id, "passed-company")
        api_ctor.assert_called_once_with("passed-ozon-key", "passed-company")
        get_accounts.assert_not_called()
        legacy_get.assert_not_called()

        status = bot.get_status()
        self.assertEqual(status["account_id"], "ozon-main")
        self.assertEqual(status["account_name"], "Ozon Main")
        self.assertEqual(status["marketplace"], "ozon")

    def test_ozon_bot_without_account_keeps_legacy_fallback(self):
        legacy_config = {
            "enabled": True,
            "api_key": "legacy-ozon-key",
            "company_id": "legacy-company",
        }
        api_client = mock.Mock()
        api_client.get_review_count.return_value = {}

        with mock.patch.object(ozon_bot_module, "OzonAPI", return_value=api_client) as api_ctor, \
             mock.patch.object(ozon_bot_module.config, "get_accounts", return_value=[]), \
             mock.patch.object(ozon_bot_module.config, "get", return_value=legacy_config):
            bot = ozon_bot_module.OzonBot()
            result = bot.connect()

        self.assertTrue(result)
        api_ctor.assert_called_once_with("legacy-ozon-key", "legacy-company")
        status = bot.get_status()
        self.assertEqual(status["account_id"], "ozon-legacy")
        self.assertEqual(status["account_name"], "Ozon")
        self.assertEqual(status["marketplace"], "ozon")

    def test_wildberries_bot_uses_passed_account_instead_of_global_config(self):
        account = {
            "id": "wb-main",
            "name": "WB Main",
            "marketplace": "wildberries",
            "enabled": True,
            "api_key": "passed-wb-key",
            "company_id": "",
        }
        api_client = mock.Mock()
        api_client.get_unanswered_count.return_value = 1

        with mock.patch.object(wildberries_bot_module, "WBAPI", return_value=api_client) as api_ctor, \
             mock.patch.object(wildberries_bot_module.config, "get_accounts") as get_accounts, \
             mock.patch.object(wildberries_bot_module.config, "get") as legacy_get:
            bot = wildberries_bot_module.WildberriesBot(account=account)
            result = bot.connect()

        self.assertTrue(result)
        self.assertEqual(bot.api_key, "passed-wb-key")
        api_ctor.assert_called_once_with("passed-wb-key")
        get_accounts.assert_not_called()
        legacy_get.assert_not_called()

        status = bot.get_status()
        self.assertEqual(status["account_id"], "wb-main")
        self.assertEqual(status["account_name"], "WB Main")
        self.assertEqual(status["marketplace"], "wildberries")

    def test_wildberries_bot_without_account_keeps_legacy_fallback(self):
        legacy_config = {
            "enabled": True,
            "api_key": "legacy-wb-key",
        }
        api_client = mock.Mock()
        api_client.get_unanswered_count.return_value = 1

        with mock.patch.object(wildberries_bot_module, "WBAPI", return_value=api_client) as api_ctor, \
             mock.patch.object(wildberries_bot_module.config, "get_accounts", return_value=[]), \
             mock.patch.object(wildberries_bot_module.config, "get", return_value=legacy_config):
            bot = wildberries_bot_module.WildberriesBot()
            result = bot.connect()

        self.assertTrue(result)
        api_ctor.assert_called_once_with("legacy-wb-key")
        status = bot.get_status()
        self.assertEqual(status["account_id"], "wildberries-legacy")
        self.assertEqual(status["account_name"], "Wildberries")
        self.assertEqual(status["marketplace"], "wildberries")

    def test_wildberries_bot_connect_fails_when_probe_returns_empty_dict(self):
        account = {
            "id": "wb-main",
            "name": "WB Main",
            "marketplace": "wildberries",
            "enabled": True,
            "api_key": "passed-wb-key",
            "company_id": "",
        }
        api_client = mock.Mock()
        api_client.get_unanswered_count.return_value = {}

        with mock.patch.object(wildberries_bot_module, "WBAPI", return_value=api_client), \
             mock.patch.object(wildberries_bot_module.config, "get_accounts") as get_accounts, \
             mock.patch.object(wildberries_bot_module.config, "get") as legacy_get:
            bot = wildberries_bot_module.WildberriesBot(account=account)
            result = bot.connect()

        self.assertFalse(result)
        get_accounts.assert_not_called()
        legacy_get.assert_not_called()

    def test_wildberries_bot_connect_fails_when_probe_returns_none(self):
        account = {
            "id": "wb-main",
            "name": "WB Main",
            "marketplace": "wildberries",
            "enabled": True,
            "api_key": "passed-wb-key",
            "company_id": "",
        }
        api_client = mock.Mock()
        api_client.get_unanswered_count.return_value = None

        with mock.patch.object(wildberries_bot_module, "WBAPI", return_value=api_client):
            bot = wildberries_bot_module.WildberriesBot(account=account)
            result = bot.connect()

        self.assertFalse(result)

    def test_wildberries_bot_connect_succeeds_only_with_valid_probe(self):
        account = {
            "id": "wb-main",
            "name": "WB Main",
            "marketplace": "wildberries",
            "enabled": True,
            "api_key": "passed-wb-key",
            "company_id": "",
        }
        api_client = mock.Mock()
        api_client.get_unanswered_count.return_value = {"countUnanswered": 0}

        with mock.patch.object(wildberries_bot_module, "WBAPI", return_value=api_client):
            bot = wildberries_bot_module.WildberriesBot(account=account)
            result = bot.connect()

        self.assertTrue(result)


class FakeConfig:
    def __init__(self, accounts):
        self.accounts = list(accounts)

    def get_accounts(self):
        return [dict(account) for account in self.accounts]


class FakeManagedBot:
    def __init__(self, account=None):
        self.account = dict(account or {})
        self.account_id = self.account.get("id")
        self.account_name = self.account.get("name")
        self.marketplace = self.account.get("marketplace")
        self.running = False
        self.start_calls = 0
        self.stop_calls = 0

    def set_account(self, account):
        self.account = dict(account)
        self.account_id = self.account.get("id")
        self.account_name = self.account.get("name")
        self.marketplace = self.account.get("marketplace")

    def start(self):
        self.start_calls += 1
        if self.running:
            return False
        self.running = True
        return True

    def stop(self):
        self.stop_calls += 1
        self.running = False
        return True

    def get_status(self):
        return {
            "running": self.running,
            "stopping": False,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "marketplace": self.marketplace,
        }


class BotManagerTests(unittest.TestCase):
    def setUp(self):
        self.accounts = [
            {
                "id": "ozon-main",
                "name": "Ozon Main",
                "marketplace": "ozon",
                "enabled": True,
                "api_key": "ozon-key-1",
                "company_id": "company-1",
            },
            {
                "id": "wb-main",
                "name": "WB Main",
                "marketplace": "wildberries",
                "enabled": False,
                "api_key": "wb-key-1",
                "company_id": "",
            },
            {
                "id": "ozon-second",
                "name": "Ozon Second",
                "marketplace": "ozon",
                "enabled": True,
                "api_key": "ozon-key-2",
                "company_id": "company-2",
            },
        ]

    def _make_manager(self):
        return bot_manager_module.BotManager(config_manager=FakeConfig(self.accounts))

    def test_manager_creates_separate_bots_for_different_account_ids(self):
        manager = self._make_manager()

        with mock.patch.object(
            bot_manager_module.BotManager,
            "BOT_CLASSES",
            {"ozon": FakeManagedBot, "wildberries": FakeManagedBot},
        ):
            bot_one = manager.create_bot(self.accounts[0])
            bot_two = manager.create_bot(self.accounts[1])

        self.assertIsNot(bot_one, bot_two)
        self.assertEqual(set(manager.bots), {"ozon-main", "wb-main"})

    def test_manager_rejects_duplicate_account_id(self):
        manager = self._make_manager()

        with mock.patch.object(
            bot_manager_module.BotManager,
            "BOT_CLASSES",
            {"ozon": FakeManagedBot, "wildberries": FakeManagedBot},
        ):
            manager.create_bot(self.accounts[0])

            with self.assertRaises(ValueError):
                manager.create_bot(dict(self.accounts[0]))

    def test_manager_start_stop_and_status_for_specific_account_and_all_accounts(self):
        manager = self._make_manager()

        with mock.patch.object(
            bot_manager_module.BotManager,
            "BOT_CLASSES",
            {"ozon": FakeManagedBot, "wildberries": FakeManagedBot},
        ):
            self.assertTrue(manager.start_account("ozon-main"))

            statuses = manager.get_statuses()
            self.assertTrue(statuses["ozon-main"]["running"])
            self.assertFalse(statuses["wb-main"]["running"])
            self.assertEqual(statuses["wb-main"]["account_name"], "WB Main")

            start_results = manager.start_all_enabled()
            self.assertEqual(start_results, {"ozon-main": False, "ozon-second": True})
            self.assertEqual(set(manager.bots), {"ozon-main", "ozon-second"})

            self.assertTrue(manager.stop_account("ozon-main"))
            self.assertFalse(manager.get_statuses()["ozon-main"]["running"])

            stop_results = manager.stop_all()
            self.assertEqual(stop_results, {"ozon-main": True, "ozon-second": True})

            final_statuses = manager.get_statuses()
            self.assertFalse(final_statuses["ozon-main"]["running"])
            self.assertFalse(final_statuses["ozon-second"]["running"])
            self.assertFalse(final_statuses["wb-main"]["running"])
