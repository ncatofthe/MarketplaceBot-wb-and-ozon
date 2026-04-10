import json
import sys
import types
import unittest
from importlib import util
from pathlib import Path
from unittest import mock


ROOT_DIR = Path(__file__).resolve().parents[1]
OZON_API_PATH = ROOT_DIR / "api" / "ozon_api.py"
WB_API_PATH = ROOT_DIR / "api" / "wb_api.py"


class FakeTimeout(Exception):
    pass


class FakeConnectionError(Exception):
    pass


class FakeRequestException(Exception):
    pass


def build_fake_requests_module():
    fake_requests = types.ModuleType("requests")

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def post(self, *args, **kwargs):
            raise NotImplementedError

        def get(self, *args, **kwargs):
            raise NotImplementedError

    fake_requests.Session = FakeSession
    fake_requests.exceptions = types.SimpleNamespace(
        Timeout=FakeTimeout,
        ConnectionError=FakeConnectionError,
        RequestException=FakeRequestException,
    )
    return fake_requests


def load_module(module_name, file_path):
    fake_requests = build_fake_requests_module()
    previous_requests = sys.modules.get("requests")
    sys.modules["requests"] = fake_requests
    try:
        spec = util.spec_from_file_location(module_name, file_path)
        module = util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        if previous_requests is None:
            del sys.modules["requests"]
        else:
            sys.modules["requests"] = previous_requests
    return module


OZON_MODULE = load_module("test_ozon_api_module", OZON_API_PATH)
WB_MODULE = load_module("test_wb_api_module", WB_API_PATH)


class FakeResponse:
    def __init__(self, status_code, json_data=None, text="", json_error=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_data


class OzonApiTests(unittest.TestCase):
    def setUp(self):
        self.api = OZON_MODULE.OzonAPI("api-key", "company-id")
        self.api.session = mock.Mock()

    def test_ozon_200_ok_uses_timeout_and_returns_json(self):
        self.api.session.post.return_value = FakeResponse(200, json_data={"result": "ok"})

        result = self.api.get_review_count()

        self.assertEqual(result, {"result": "ok"})
        _, kwargs = self.api.session.post.call_args
        self.assertEqual(kwargs["timeout"], self.api.REQUEST_TIMEOUT)

    def test_ozon_403_returns_controlled_error_after_retries(self):
        self.api.session.post.return_value = FakeResponse(403, text="forbidden")

        with mock.patch.object(OZON_MODULE.time, "sleep") as sleep_mock:
            result = self.api.get_review_count()

        self.assertEqual(result["error"], "antibot")
        self.assertEqual(result["status_code"], 403)
        self.assertEqual(self.api.session.post.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    def test_ozon_timeout_returns_controlled_error(self):
        self.api.session.post.side_effect = OZON_MODULE.requests.exceptions.Timeout("slow request")

        with mock.patch.object(OZON_MODULE.time, "sleep") as sleep_mock:
            result = self.api.get_review_count()

        self.assertEqual(result["error"], "timeout")
        self.assertEqual(self.api.session.post.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    def test_ozon_invalid_json_returns_controlled_error(self):
        self.api.session.post.return_value = FakeResponse(
            200,
            text="not-json",
            json_error=json.JSONDecodeError("bad json", "not-json", 0),
        )

        result = self.api.get_review_count()

        self.assertEqual(result["error"], "invalid_json")

    def test_ozon_get_unanswered_reviews_handles_none_response_safely(self):
        with mock.patch.object(self.api, "get_review_list", return_value=None):
            result = self.api.get_unanswered_reviews()

        self.assertEqual(result, [])


class WbApiTests(unittest.TestCase):
    def setUp(self):
        self.api = WB_MODULE.WBAPI("api-key")
        self.api.session = mock.Mock()
        self.api._rate_limit_sleep = mock.Mock()

    def test_wb_200_ok_uses_timeout_and_returns_data(self):
        self.api.session.get.return_value = FakeResponse(
            200,
            json_data={"error": False, "data": {"countUnanswered": 7}},
        )

        result = self.api.get_unanswered_count()

        self.assertEqual(result, {"countUnanswered": 7})
        _, kwargs = self.api.session.get.call_args
        self.assertEqual(kwargs["timeout"], self.api.REQUEST_TIMEOUT)

    def test_wb_429_retries_with_backoff_and_recovers(self):
        self.api.session.get.side_effect = [
            FakeResponse(
                429,
                json_data={"error": True, "errorText": "rate limited", "additionalErrors": []},
                text="rate limited",
            ),
            FakeResponse(
                200,
                json_data={"error": False, "data": {"countUnanswered": 3}},
            ),
        ]

        with mock.patch.object(WB_MODULE.time, "sleep") as sleep_mock, \
             mock.patch.object(WB_MODULE.random, "uniform", return_value=0):
            result = self.api._make_request("GET", "feedbacks/count-unanswered")

        self.assertEqual(result, {"countUnanswered": 3})
        self.assertEqual(self.api.session.get.call_count, 2)
        sleep_mock.assert_called_once_with(1)

    def test_wb_timeout_returns_none(self):
        self.api.session.get.side_effect = WB_MODULE.requests.exceptions.Timeout("slow request")

        with mock.patch.object(WB_MODULE.time, "sleep") as sleep_mock:
            result = self.api._make_request("GET", "feedbacks")

        self.assertIsNone(result)
        self.assertEqual(self.api.session.get.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    def test_wb_invalid_json_returns_none(self):
        self.api.session.get.return_value = FakeResponse(
            200,
            text="not-json",
            json_error=json.JSONDecodeError("bad json", "not-json", 0),
        )

        result = self.api._make_request("GET", "feedbacks")

        self.assertIsNone(result)
