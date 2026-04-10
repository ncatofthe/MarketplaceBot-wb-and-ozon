import unittest
from importlib import util
from pathlib import Path
from unittest import mock
import tempfile

from utils.review_state import ReviewStateStore

BASE_BOT_PATH = Path(__file__).resolve().parents[1] / "bots" / "base_bot.py"
SPEC = util.spec_from_file_location("test_base_bot_module", BASE_BOT_PATH)
BASE_BOT_MODULE = util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BASE_BOT_MODULE)
BaseBot = BASE_BOT_MODULE.BaseBot


class FakeThread:
    def __init__(self, alive=True):
        self.alive = alive
        self.join_calls = []
        self.start_calls = 0

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        self.join_calls.append(timeout)

    def start(self):
        self.start_calls += 1


class FakeStopEvent:
    def __init__(self):
        self._is_set = False
        self.wait_calls = []

    def is_set(self):
        return self._is_set

    def wait(self, timeout):
        self.wait_calls.append(timeout)
        self._is_set = True
        return True

    def set(self):
        self._is_set = True

    def clear(self):
        self._is_set = False


class DummyBot(BaseBot):
    def __init__(self, connect_result=False):
        super().__init__()
        self.connect_result = connect_result
        self.connect_calls = 0

    def connect(self):
        self.connect_calls += 1
        return self.connect_result

    def get_unanswered_reviews(self):
        return []

    def send_answer(self, review_id, text):
        return True


class ReviewBot(BaseBot):
    def __init__(
        self,
        *,
        reviews=None,
        connect_result=True,
        connect_exception=None,
        reviews_exception=None,
        send_results=None,
        review_state=None,
        account_id=None,
        marketplace="ozon",
    ):
        super().__init__(review_state=review_state)
        self.reviews = reviews if reviews is not None else []
        self.connect_result = connect_result
        self.connect_exception = connect_exception
        self.reviews_exception = reviews_exception
        self.send_results = send_results or {}
        self.send_calls = []
        self.account_id = account_id
        self.marketplace = marketplace

    def connect(self):
        if self.connect_exception:
            raise self.connect_exception
        return self.connect_result

    def get_unanswered_reviews(self):
        if self.reviews_exception:
            raise self.reviews_exception
        return list(self.reviews)

    def send_answer(self, review_id, text):
        self.send_calls.append(review_id)
        return self.send_results.get(review_id, True)


def fake_config_get(section, key=None):
    values = {
        ("general", "check_interval"): 10,
        ("general", "min_stars"): 4,
        ("general", "max_answers_per_run"): -1,
        ("general", "short_sleep"): 0,
    }
    return values[(section, key)]


class BaseBotLifecycleTests(unittest.TestCase):
    def test_failed_connect_waits_before_retry(self):
        bot = DummyBot(connect_result=False)
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", return_value=10):
            bot._run()

        self.assertEqual(bot.connect_calls, 1)
        self.assertEqual(bot.stop_event.wait_calls, [60])
        self.assertFalse(bot.is_running)

    def test_stop_returns_false_when_thread_did_not_finish(self):
        bot = DummyBot(connect_result=True)
        bot.thread = FakeThread(alive=True)
        bot.is_running = True

        result = bot.stop()

        self.assertFalse(result)
        self.assertTrue(bot.is_running)
        self.assertEqual(bot.thread.join_calls, [10])

    def test_start_is_blocked_when_live_thread_exists_even_if_flag_false(self):
        bot = DummyBot(connect_result=True)
        live_thread = FakeThread(alive=True)
        bot.thread = live_thread
        bot.is_running = False

        with mock.patch.object(BASE_BOT_MODULE.threading, "Thread") as thread_ctor:
            result = bot.start()

        self.assertFalse(result)
        self.assertTrue(bot.is_running)
        self.assertIs(bot.thread, live_thread)
        thread_ctor.assert_not_called()


class BaseBotStatsTests(unittest.TestCase):
    def test_stats_for_empty_reviews(self):
        bot = ReviewBot(reviews=[])
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
            bot._run()

        status = bot.get_status()
        self.assertEqual(status["found_reviews"], 0)
        self.assertEqual(status["processed_reviews"], 0)
        self.assertEqual(status["answered_reviews"], 0)
        self.assertEqual(status["skipped_reviews"], 0)
        self.assertEqual(status["error_count"], 0)
        self.assertIsNotNone(status["last_run_started_at"])
        self.assertIsNotNone(status["last_run_finished_at"])
        self.assertEqual(status["last_success_at"], status["last_run_finished_at"])

    def test_stats_for_successful_send(self):
        bot = ReviewBot(reviews=[{"id": "r1", "rating": 5, "text": "ok"}])
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
            bot._run()

        status = bot.get_status()
        self.assertEqual(status["found_reviews"], 1)
        self.assertEqual(status["processed_reviews"], 1)
        self.assertEqual(status["answered_reviews"], 1)
        self.assertEqual(status["skipped_reviews"], 0)
        self.assertEqual(status["error_count"], 0)
        self.assertEqual(status["last_success_at"], status["last_run_finished_at"])

    def test_stats_for_skipped_review_by_min_stars(self):
        bot = ReviewBot(reviews=[{"id": "r1", "rating": 3, "text": "skip"}])
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
            bot._run()

        status = bot.get_status()
        self.assertEqual(status["found_reviews"], 1)
        self.assertEqual(status["processed_reviews"], 1)
        self.assertEqual(status["answered_reviews"], 0)
        self.assertEqual(status["skipped_reviews"], 1)
        self.assertEqual(status["error_count"], 0)

    def test_stats_for_send_error(self):
        bot = ReviewBot(
            reviews=[{"id": "r1", "rating": 5, "text": "fail"}],
            send_results={"r1": False},
        )
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
            bot._run()

        status = bot.get_status()
        self.assertEqual(status["found_reviews"], 1)
        self.assertEqual(status["processed_reviews"], 1)
        self.assertEqual(status["answered_reviews"], 0)
        self.assertEqual(status["error_count"], 1)
        self.assertIn("r1", status["last_error"])
        self.assertIsNone(status["last_success_at"])

    def test_stats_for_exception_in_process_reviews(self):
        bot = ReviewBot(reviews_exception=RuntimeError("boom in process"))
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
            bot._run()

        status = bot.get_status()
        self.assertEqual(status["error_count"], 1)
        self.assertIn("boom in process", status["last_error"])
        self.assertIsNotNone(status["last_run_started_at"])
        self.assertIsNotNone(status["last_run_finished_at"])
        self.assertIsNone(status["last_success_at"])

    def test_stats_for_exception_in_main_cycle(self):
        bot = ReviewBot(connect_exception=RuntimeError("boom in connect"))
        bot.stop_event = FakeStopEvent()

        with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
            bot._run()

        status = bot.get_status()
        self.assertEqual(status["error_count"], 1)
        self.assertIn("boom in connect", status["last_error"])
        self.assertIsNotNone(status["last_run_started_at"])
        self.assertIsNotNone(status["last_run_finished_at"])
        self.assertIsNone(status["last_success_at"])


class BaseBotPersistentDeduplicationTests(unittest.TestCase):
    def _make_store(self, temp_dir, max_entries_per_account=2000):
        return ReviewStateStore(
            state_file=Path(temp_dir) / "review_state.json",
            max_entries_per_account=max_entries_per_account,
        )

    def test_successful_send_is_recorded_in_persistent_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._make_store(temp_dir)
            bot = ReviewBot(
                reviews=[{"id": "r1", "rating": 5, "text": "ok"}],
                review_state=store,
                account_id="acc-1",
                marketplace="ozon",
            )
            bot.stop_event = FakeStopEvent()

            with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
                bot._run()

            self.assertEqual(bot.send_calls, ["r1"])
            self.assertTrue(store.has_processed("ozon", "acc-1", "r1"))

    def test_duplicate_review_for_same_account_is_skipped_after_reload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._make_store(temp_dir)
            first_bot = ReviewBot(
                reviews=[{"id": "r1", "rating": 5, "text": "ok"}],
                review_state=store,
                account_id="acc-1",
                marketplace="ozon",
            )
            first_bot.stop_event = FakeStopEvent()

            with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
                first_bot._run()

            reloaded_store = self._make_store(temp_dir)
            second_bot = ReviewBot(
                reviews=[{"id": "r1", "rating": 5, "text": "ok again"}],
                review_state=reloaded_store,
                account_id="acc-1",
                marketplace="ozon",
            )
            second_bot.stop_event = FakeStopEvent()

            with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
                second_bot._run()

            status = second_bot.get_status()
            self.assertEqual(second_bot.send_calls, [])
            self.assertEqual(status["processed_reviews"], 1)
            self.assertEqual(status["answered_reviews"], 0)
            self.assertEqual(status["skipped_reviews"], 1)
            self.assertTrue(reloaded_store.has_processed("ozon", "acc-1", "r1"))

    def test_same_review_id_for_other_account_is_not_treated_as_duplicate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._make_store(temp_dir)
            first_bot = ReviewBot(
                reviews=[{"id": "shared-review", "rating": 5, "text": "first"}],
                review_state=store,
                account_id="acc-1",
                marketplace="ozon",
            )
            second_bot = ReviewBot(
                reviews=[{"id": "shared-review", "rating": 5, "text": "second"}],
                review_state=store,
                account_id="acc-2",
                marketplace="ozon",
            )
            first_bot.stop_event = FakeStopEvent()
            second_bot.stop_event = FakeStopEvent()

            with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
                first_bot._run()
                second_bot._run()

            self.assertEqual(first_bot.send_calls, ["shared-review"])
            self.assertEqual(second_bot.send_calls, ["shared-review"])
            self.assertTrue(store.has_processed("ozon", "acc-1", "shared-review"))
            self.assertTrue(store.has_processed("ozon", "acc-2", "shared-review"))

    def test_failed_send_is_not_saved_in_persistent_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._make_store(temp_dir)
            bot = ReviewBot(
                reviews=[{"id": "r1", "rating": 5, "text": "fail"}],
                send_results={"r1": False},
                review_state=store,
                account_id="acc-1",
                marketplace="ozon",
            )
            bot.stop_event = FakeStopEvent()

            with mock.patch.object(BASE_BOT_MODULE.config, "get", side_effect=fake_config_get):
                bot._run()

            self.assertEqual(bot.send_calls, ["r1"])
            self.assertFalse(store.has_processed("ozon", "acc-1", "r1"))
