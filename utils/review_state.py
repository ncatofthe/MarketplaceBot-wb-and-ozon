"""
Persistent anti-duplicate state для успешно обработанных отзывов.
"""
import copy
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from runtime_paths import get_runtime_paths


RUNTIME_PATHS = get_runtime_paths()
STATE_FILE = RUNTIME_PATHS.settings_dir / "review_state.json"
DEFAULT_MAX_ENTRIES_PER_ACCOUNT = 2000


def _utc_timestamp():
    """Текущее UTC-время в стабильном ISO-формате."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReviewStateStore:
    """Простое JSON-хранилище обработанных отзывов по аккаунтам."""

    def __init__(self, state_file=None, max_entries_per_account=DEFAULT_MAX_ENTRIES_PER_ACCOUNT):
        self.state_file = Path(state_file or STATE_FILE)
        self.max_entries_per_account = max(1, int(max_entries_per_account))
        self._lock = threading.Lock()
        self._logger = logging.getLogger("MarketplaceBot")
        self._state = self._load_state()

    @staticmethod
    def _empty_state():
        """Базовая структура state."""
        return {
            "version": 1,
            "accounts": {},
        }

    @staticmethod
    def _normalize_key_part(value):
        """Нормализация значения для account/review ключей."""
        normalized = str(value or "").strip()
        return normalized or None

    @classmethod
    def _account_storage_key(cls, marketplace, account_id):
        """Внутренний ключ хранения для аккаунта."""
        marketplace = cls._normalize_key_part(marketplace)
        account_id = cls._normalize_key_part(account_id)
        if marketplace is None or account_id is None:
            return None
        return f"{marketplace}:{account_id}"

    def _normalize_state(self, state):
        """Нормализация прочитанного JSON в ожидаемую структуру."""
        normalized = self._empty_state()
        if not isinstance(state, dict):
            return normalized

        normalized["version"] = state.get("version", 1)
        accounts = state.get("accounts", {})
        if not isinstance(accounts, dict):
            return normalized

        for account_key, account_entry in accounts.items():
            if not isinstance(account_entry, dict):
                continue

            reviews = account_entry.get("reviews", {})
            if not isinstance(reviews, dict):
                continue

            normalized_reviews = {}
            for review_id, processed_at in reviews.items():
                normalized_review_id = self._normalize_key_part(review_id)
                if normalized_review_id is None:
                    continue
                normalized_reviews[normalized_review_id] = str(processed_at or "")

            if not normalized_reviews:
                continue

            normalized["accounts"][str(account_key)] = {
                "marketplace": self._normalize_key_part(account_entry.get("marketplace")),
                "account_id": self._normalize_key_part(account_entry.get("account_id")),
                "reviews": self._pruned_reviews(normalized_reviews),
            }

        return normalized

    def _load_state(self):
        """Загрузка JSON state с безопасным fallback."""
        if not self.state_file.exists():
            return self._empty_state()

        try:
            with open(self.state_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            return self._normalize_state(data)
        except (json.JSONDecodeError, OSError, IOError) as error:
            self._logger.warning(f"Review state load failed: {error}")
            return self._empty_state()

    def reload(self):
        """Перезагрузка state с диска."""
        with self._lock:
            self._state = self._load_state()
            return copy.deepcopy(self._state)

    def _persist_state(self, state):
        """Атомарная запись state на диск."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.state_file.with_suffix(f"{self.state_file.suffix}.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(temp_file, self.state_file)
            if os.name != "nt":
                try:
                    os.chmod(self.state_file, 0o600)
                except OSError:
                    pass
            return True
        except (OSError, IOError) as error:
            self._logger.warning(f"Review state save failed: {error}")
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except OSError:
                pass
            return False

    def _pruned_reviews(self, reviews):
        """Retention по количеству последних успешно обработанных отзывов."""
        if len(reviews) <= self.max_entries_per_account:
            return dict(reviews)

        sorted_reviews = sorted(reviews.items(), key=lambda item: item[1])
        kept_reviews = sorted_reviews[-self.max_entries_per_account :]
        return {review_id: processed_at for review_id, processed_at in kept_reviews}

    def has_processed(self, marketplace, account_id, review_id):
        """Проверка, был ли отзыв уже успешно обработан."""
        storage_key = self._account_storage_key(marketplace, account_id)
        review_id = self._normalize_key_part(review_id)
        if storage_key is None or review_id is None:
            return False

        with self._lock:
            account_entry = self._state["accounts"].get(storage_key, {})
            reviews = account_entry.get("reviews", {})
            return review_id in reviews

    def mark_processed(self, marketplace, account_id, review_id, processed_at=None):
        """Пометка успешно обработанного отзыва с персистентным сохранением."""
        storage_key = self._account_storage_key(marketplace, account_id)
        review_id = self._normalize_key_part(review_id)
        if storage_key is None or review_id is None:
            return False

        processed_at = str(processed_at or _utc_timestamp())

        with self._lock:
            updated_state = copy.deepcopy(self._state)
            account_entry = updated_state["accounts"].setdefault(
                storage_key,
                {
                    "marketplace": self._normalize_key_part(marketplace),
                    "account_id": self._normalize_key_part(account_id),
                    "reviews": {},
                },
            )
            account_entry["reviews"][review_id] = processed_at
            account_entry["reviews"] = self._pruned_reviews(account_entry["reviews"])

            if not self._persist_state(updated_state):
                return False

            self._state = updated_state
            return True

    def get_account_reviews(self, marketplace, account_id):
        """Тестовый/helper доступ к review ids аккаунта."""
        storage_key = self._account_storage_key(marketplace, account_id)
        if storage_key is None:
            return {}

        with self._lock:
            account_entry = self._state["accounts"].get(storage_key, {})
            return copy.deepcopy(account_entry.get("reviews", {}))


review_state_store = ReviewStateStore()
