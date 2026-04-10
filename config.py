"""
Конфигурация приложения
"""
import copy
import json
import logging
import os
from runtime_assets import ensure_bundled_example_assets
from runtime_paths import get_runtime_paths
from secure_storage import (
    SecretStorageError,
    protect_secret,
    unprotect_secret,
)

# Директории
RUNTIME_PATHS = get_runtime_paths()
BASE_DIR = RUNTIME_PATHS.base_dir
SETTINGS_DIR = RUNTIME_PATHS.settings_dir
LOGS_DIR = RUNTIME_PATHS.logs_dir
BUNDLED_SETTINGS_DIR = BASE_DIR / "settings"

# Файлы настроек
LEGACY_CONFIG_FILE = SETTINGS_DIR / "config.json"
CONFIG_EXAMPLE_FILE = SETTINGS_DIR / "config.example.json"
CONFIG_LOCAL_FILE = SETTINGS_DIR / "config.local.json"
ANSWERS_FILE = SETTINGS_DIR / "answers.json"
ANSWERS_EXAMPLE_FILE = SETTINGS_DIR / "answers.example.json"
ANSWERS_LOCAL_FILE = SETTINGS_DIR / "answers.local.json"

ENV_CONFIG_OVERRIDES = {
    ("ozon", "api_key"): ("MARKETPLACEBOT_OZON_API_KEY",),
    ("ozon", "company_id"): ("MARKETPLACEBOT_OZON_COMPANY_ID",),
    ("wildberries", "api_key"): (
        "MARKETPLACEBOT_WB_API_KEY",
        "MARKETPLACEBOT_WILDBERRIES_API_KEY",
    ),
}
ACCOUNT_MARKETPLACES = ("ozon", "wildberries")

# Настройки по умолчанию
DEFAULT_CONFIG = {
    "ozon": {
        "enabled": False,
        "api_key": "",
        "company_id": "",
        "use_api": True,
    },
    "wildberries": {
        "enabled": False,
        "api_key": "",
        "use_api": True,
    },
    "general": {
        "check_interval": 60,  # минуты
        "min_stars": 1,  # минимальное количество звезд для ответа (по умолчанию 1)
        "max_answers_per_run": -1,  # -1 = без ограничений
        "short_sleep": 0.5,  # задержка между запросами
        "log_level": "INFO",
    },
}

# Шаблоны ответов по умолчанию
DEFAULT_ANSWERS = {
    "greetings": [
        "Здравствуйте!",
        "Добрый день!",
    ],
    "gratitude": [
        "Спасибо, что выбрали нашу продукцию!",
        "Мы рады, что Вы обратили внимание на нашу продукцию!",
        "Очень рады вашей обратной связи!",
        "Очень рады, что Вы остались довольны нашим продуктом!",
        "Спасибо за уделенное время и за то, что поделились Вашим впечатлением.",
        "Большое спасибо за хороший отзыв!",
        "Большое спасибо за положительный отзыв!",
        "Благодарим за покупку и за отзыв!",
        "Очень приятно, что товар вам понравился и заслужил высокую оценку!",
        "Мы очень рады, что Вы остались довольны покупкой.",
        "Спасибо за такую высокую оценку! Мы работаем для Вас!",
        "Благодарим Вас за отзыв, он очень важен для нас!",
        "Мы очень рады, что среди нашей продукции Вы нашли нужный товар!",
        "Спасибо, что Вы выбрали наш бренд!",
        "Спасибо, что Вы выбрали нашу марку!",
        "Спасибо, что Вы выбрали нашу компанию!",
        "Спасибо за отзыв, мы очень ценим обратную связь с Вами!",
    ],
    "gratitude_no_comment": [
        "Спасибо, что выбрали нашу продукцию!",
        "Мы рады, что Вы обратили внимание на нашу продукцию!",
        "Очень рады, что Вы остались довольны нашим продуктом!",
        "Большое спасибо за положительную оценку!",
        "Благодарим за покупку и за оценку!",
        "Очень приятно, что товар вам понравился и заслужил высокую оценку!",
        "Мы очень рады, что Вы остались довольны покупкой.",
        "Спасибо за такую высокую оценку! Мы работаем для Вас!",
        "Спасибо, что Вы выбрали наш бренд!",
        "Спасибо, что Вы выбрали нашу марку!",
        "Спасибо, что Вы выбрали нашу компанию!",
        "Спасибо за оценку, мы очень ценим обратную связь с Вами!",
    ],
    "apologies": [
        "Нам жаль, что мы не смогли оправдать Ваши ожидания.",
        "Нам очень жаль.",
        "Приносим свои извинения.",
    ],
    "examination": [
        "Мы разберемся с данным вопросом.",
        "Мы обязательно разберемся с данным вопросом.",
        "Мы проработаем ваш отзыв.",
        "Мы обязательно возьмем на заметку Ваш комментарий.",
    ],
    "main": [
        "Нам будет приятно видеть Вас в числе наших постоянных покупателей.",
        "Нам будет очень приятно увидеть Вас снова в числе наших покупателей!",
        "Нам будет приятно видеть Вас в числе наших постоянных покупателей.",
    ],
    "recommendations": [
        "Обратите внимание на другие наши товары.",
        "Рассмотрите также наши новинки.",
        "Рекомендуем Вам приобрести и другие товары из данной линейки.",
        "Рекомендуем посетить наш магазин или любой наш отдельный бренд, чтобы ознакомиться с полным ассортиментом.",
        "Наш ассортимент всегда пополняется, возможно, Вам будет интересно взглянуть на наши новинки.",
        "Добавляйте наш бренд в \"Любимые\", чтобы следить за новинками и акциями!",
    ],
    "goodbye": [
        "С уважением, представитель бренда.",
        "Искренне Ваша команда.",
        "С уважением, команда поддержки.",
    ],
    "5": [
        "Спасибо за Ваши 5 звездочек!",
    ],
    "4": [
        "Спасибо за Ваши 4 звездочки!",
    ],
    "3": [
        "Cпасибо за отзыв.",
        "Спасибо за уделенное время и за то, что поделились Вашим впечатлением.",
        "Спасибо за честный отзыв, он очень важен для нас.",
        "Нам жаль, что мы не смогли получить более высокую оценку нашей продукции. Мы верим, что в следующий раз оправдаем Ваши ожидания.",
    ],
    "3_no_comment": [
        "Cпасибо за оценку.",
        "Спасибо за честную оценку, она очень важна для нас.",
        "Нам жаль, что мы не смогли получить более высокую оценку нашей продукции. Мы верим, что в следующий раз оправдаем Ваши ожидания.",
    ],
    "2": [
        "Нам жаль, что Вы оценили наш продукт всего на 2 звездочки.",
    ],
    "1": [
        "Нам жаль, что Вы оценили наш продукт всего на 1 звездочку.",
    ],
    "0": [
        "Нам жаль, что мы Вас разочаровали.",
    ],
    "stop_words": [],
}


def _marketplace_display_name(marketplace):
    """Человекочитаемое имя маркетплейса."""
    return "Ozon" if marketplace == "ozon" else "Wildberries"


def _normalize_marketplace(marketplace):
    """Нормализация значения marketplace."""
    normalized = str(marketplace or "").strip().lower()
    return normalized if normalized in ACCOUNT_MARKETPLACES else None


def _default_account_name(marketplace, index):
    """Имя аккаунта по умолчанию."""
    base_name = _marketplace_display_name(marketplace)
    return base_name if index == 0 else f"{base_name} {index + 1}"


def _normalize_account(account, index):
    """Нормализация одного аккаунта."""
    if not isinstance(account, dict):
        return None

    normalized = copy.deepcopy(account)
    marketplace = _normalize_marketplace(normalized.get("marketplace"))
    if not marketplace:
        return None

    normalized["marketplace"] = marketplace
    normalized["id"] = str(normalized.get("id") or f"{marketplace}-{index + 1}")
    normalized["name"] = str(normalized.get("name") or _default_account_name(marketplace, index))
    normalized["enabled"] = bool(normalized.get("enabled", False))
    normalized["api_key"] = str(normalized.get("api_key") or "")
    normalized["company_id"] = str(normalized.get("company_id") or "") if marketplace == "ozon" else ""
    return normalized


def _normalize_accounts(accounts):
    """Нормализация списка аккаунтов."""
    if not isinstance(accounts, list):
        return []

    normalized_accounts = []
    for index, account in enumerate(accounts):
        normalized_account = _normalize_account(account, index)
        if normalized_account is not None:
            normalized_accounts.append(normalized_account)

    return normalized_accounts


def _get_primary_account(accounts, marketplace):
    """Получение первого аккаунта маркетплейса."""
    for account in accounts or []:
        if account.get("marketplace") == marketplace:
            return account
    return None


def _has_meaningful_legacy_account(section_data, marketplace):
    """Проверяет, можно ли синтезировать аккаунт из legacy-секции."""
    if not isinstance(section_data, dict):
        return False

    if section_data.get("enabled"):
        return True
    if section_data.get("api_key"):
        return True
    if marketplace == "ozon" and section_data.get("company_id"):
        return True
    return False


def _account_from_legacy_section(section_data, marketplace):
    """Синтезирует аккаунт из legacy-конфига."""
    if not _has_meaningful_legacy_account(section_data, marketplace):
        return None

    return _normalize_account(
        {
            "id": f"{marketplace}-1",
            "name": _marketplace_display_name(marketplace),
            "marketplace": marketplace,
            "enabled": section_data.get("enabled", False),
            "api_key": section_data.get("api_key", ""),
            "company_id": section_data.get("company_id", "") if marketplace == "ozon" else "",
        },
        index=0,
    )


def _build_legacy_section(marketplace, current_section=None, account=None):
    """Строит legacy-view секции маркетплейса."""
    current_section = current_section if isinstance(current_section, dict) else {}
    legacy_section = _deep_merge_dicts(DEFAULT_CONFIG[marketplace], current_section)

    if account is None:
        legacy_section["enabled"] = False
        legacy_section["api_key"] = ""
        if marketplace == "ozon":
            legacy_section["company_id"] = ""
        return legacy_section

    legacy_section["enabled"] = bool(account.get("enabled", False))
    legacy_section["api_key"] = str(account.get("api_key") or "")
    if marketplace == "ozon":
        legacy_section["company_id"] = str(account.get("company_id") or "")
    return legacy_section


def _sync_legacy_sections_from_accounts(config_data):
    """Синхронизирует legacy-секции из нового accounts-формата."""
    normalized_config = copy.deepcopy(config_data)
    normalized_accounts = _normalize_accounts(normalized_config.get("accounts", []))
    normalized_config["accounts"] = normalized_accounts

    for marketplace in ACCOUNT_MARKETPLACES:
        primary_account = _get_primary_account(normalized_accounts, marketplace)
        normalized_config[marketplace] = _build_legacy_section(
            marketplace,
            current_section=normalized_config.get(marketplace),
            account=primary_account,
        )

    return normalized_config


def _synthesize_accounts_from_legacy(config_data):
    """Собирает список аккаунтов из старого single-account формата."""
    accounts = []

    for marketplace in ACCOUNT_MARKETPLACES:
        account = _account_from_legacy_section(config_data.get(marketplace, {}), marketplace)
        if account is not None:
            accounts.append(account)

    return accounts


def _apply_env_override_to_accounts(config_data, marketplace, key, value):
    """Применяет env override к primary account соответствующего маркетплейса."""
    accounts = config_data.get("accounts")
    if not isinstance(accounts, list):
        return

    for index, account in enumerate(accounts):
        if account.get("marketplace") != marketplace:
            continue

        updated_account = copy.deepcopy(account)
        updated_account[key] = value
        normalized_account = _normalize_account(updated_account, index)
        if normalized_account is not None:
            accounts[index] = normalized_account
        break


def _deep_merge_dicts(base, override):
    """Рекурсивное объединение словарей конфигурации."""
    merged = copy.deepcopy(base)

    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


def _load_json_file(path):
    """Безопасно читает JSON-файл."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _log_warning(message):
    """Логирует предупреждение без импорта utils, чтобы избежать циклов."""
    logging.getLogger("MarketplaceBot").warning(message)


def _bootstrap_runtime_example_assets():
    """Копирует bundled example assets в runtime settings dir для frozen Windows."""
    if RUNTIME_PATHS.mode != "frozen-windows":
        return []

    try:
        return ensure_bundled_example_assets(
            settings_dir=SETTINGS_DIR,
            bundled_settings_dir=BUNDLED_SETTINGS_DIR,
        )
    except OSError as error:
        _log_warning(f"Не удалось bootstrap example assets: {error}")
        return []


def _apply_env_overrides(config_data):
    """Подмешивает чувствительные настройки из переменных окружения."""
    overridden = copy.deepcopy(config_data)

    for (section, key), env_names in ENV_CONFIG_OVERRIDES.items():
        for env_name in env_names:
            env_value = os.environ.get(env_name)
            if env_value:
                overridden.setdefault(section, {})
                overridden[section][key] = env_value
                _apply_env_override_to_accounts(overridden, section, key, env_value)
                break

    return overridden


def _decode_secret_value(secret_value, context):
    """Безопасная расшифровка секрета с логированием ошибок."""
    try:
        return unprotect_secret(secret_value)
    except SecretStorageError as error:
        _log_warning(f"Не удалось расшифровать {context}: {error}")
        return ""


def _decode_api_keys(config_data):
    """Расшифровывает api_key в legacy и multi-account формате."""
    decoded = copy.deepcopy(config_data)

    for marketplace in ACCOUNT_MARKETPLACES:
        section = decoded.get(marketplace)
        if isinstance(section, dict) and "api_key" in section:
            section["api_key"] = _decode_secret_value(section.get("api_key", ""), f"{marketplace}.api_key")

    accounts = decoded.get("accounts")
    if isinstance(accounts, list):
        for index, account in enumerate(accounts):
            if not isinstance(account, dict) or "api_key" not in account:
                continue
            account["api_key"] = _decode_secret_value(
                account.get("api_key", ""),
                f"accounts[{index}].api_key",
            )

    return decoded


def _encode_secret_value(secret_value, context):
    """Защищает секрет перед сохранением и пробрасывает понятную ошибку."""
    try:
        return protect_secret(secret_value)
    except SecretStorageError as error:
        raise SecretStorageError(f"Не удалось защитить {context}: {error}") from error


def _encode_api_keys(config_data):
    """Защищает api_key перед записью в local config."""
    encoded = copy.deepcopy(config_data)

    for marketplace in ACCOUNT_MARKETPLACES:
        section = encoded.get(marketplace)
        if isinstance(section, dict) and "api_key" in section:
            section["api_key"] = _encode_secret_value(section.get("api_key", ""), f"{marketplace}.api_key")

    accounts = encoded.get("accounts")
    if isinstance(accounts, list):
        for index, account in enumerate(accounts):
            if not isinstance(account, dict) or "api_key" not in account:
                continue
            account["api_key"] = _encode_secret_value(
                account.get("api_key", ""),
                f"accounts[{index}].api_key",
            )

    return encoded


class Config:
    """Класс для управления конфигурацией"""

    def __init__(self):
        _bootstrap_runtime_example_assets()
        self.config = self._load_config()
        self.answers = self._load_answers()

    def _load_config(self):
        """Загрузка конфигурации из файла."""
        config_data = copy.deepcopy(DEFAULT_CONFIG)
        config_sources = []

        if CONFIG_EXAMPLE_FILE.exists():
            config_sources.append(CONFIG_EXAMPLE_FILE)

        if CONFIG_LOCAL_FILE.exists():
            config_sources.append(CONFIG_LOCAL_FILE)
        elif LEGACY_CONFIG_FILE.exists():
            config_sources.append(LEGACY_CONFIG_FILE)

        for config_file in config_sources:
            try:
                loaded_config = _load_json_file(config_file)
                config_data = _deep_merge_dicts(config_data, loaded_config)
            except (json.JSONDecodeError, OSError, IOError) as error:
                _log_warning(f"Ошибка загрузки {config_file.name}: {error}")

        config_data = _decode_api_keys(config_data)

        if "accounts" in config_data:
            config_data = _sync_legacy_sections_from_accounts(config_data)

        return _apply_env_overrides(config_data)

    def _load_answers(self):
        """Загрузка шаблонов ответов."""
        answers_data = copy.deepcopy(DEFAULT_ANSWERS)

        answer_sources = [ANSWERS_EXAMPLE_FILE]
        if ANSWERS_LOCAL_FILE.exists():
            answer_sources.append(ANSWERS_LOCAL_FILE)
        elif ANSWERS_FILE.exists():
            answer_sources.append(ANSWERS_FILE)

        for answers_file in answer_sources:
            if not answers_file.exists():
                continue

            try:
                loaded_answers = _load_json_file(answers_file)
                answers_data = _deep_merge_dicts(answers_data, loaded_answers)
            except (json.JSONDecodeError, OSError, IOError) as error:
                _log_warning(f"Ошибка загрузки {answers_file.name}: {error}")

        return answers_data

    def save_config(self):
        """Сохранение конфигурации в файл."""
        config_to_save = copy.deepcopy(self.config)
        if "accounts" in config_to_save:
            config_to_save = _sync_legacy_sections_from_accounts(config_to_save)
        config_to_save = _encode_api_keys(config_to_save)
        CONFIG_LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_LOCAL_FILE, "w", encoding="utf-8") as file:
            json.dump(config_to_save, file, ensure_ascii=False, indent=4)
        if os.name != "nt":
            try:
                os.chmod(CONFIG_LOCAL_FILE, 0o600)
            except OSError:
                pass

    def save_answers(self):
        """Сохранение шаблонов ответов."""
        ANSWERS_LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ANSWERS_LOCAL_FILE, "w", encoding="utf-8") as file:
            json.dump(self.answers, file, ensure_ascii=False, indent=4)

    def get(self, section, key=None):
        """Получение значения из конфигурации."""
        if section in ACCOUNT_MARKETPLACES:
            section_data = self._get_marketplace_config(section)
            if key is None:
                return section_data
            return section_data.get(key)

        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key)

    def set(self, section, key, value):
        """Установка значения в конфигурации."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self._sync_account_from_legacy_section(section, key, value)

    def _get_marketplace_config(self, marketplace):
        """Legacy-совместимый view конфигурации маркетплейса."""
        if "accounts" in self.config:
            primary_account = _get_primary_account(self.config.get("accounts", []), marketplace)
            return _build_legacy_section(
                marketplace,
                current_section=self.config.get(marketplace),
                account=primary_account,
            )
        return self.config.get(marketplace, {})

    def _sync_account_from_legacy_section(self, marketplace, key, value):
        """Обновляет primary account при записи в legacy-секцию."""
        if marketplace not in ACCOUNT_MARKETPLACES:
            return
        if "accounts" not in self.config:
            return
        if key not in {"enabled", "api_key", "company_id"}:
            return

        accounts = self.config.get("accounts", [])
        for index, account in enumerate(accounts):
            if account.get("marketplace") != marketplace:
                continue

            updated_account = copy.deepcopy(account)
            if key == "enabled":
                updated_account[key] = bool(value)
            elif key == "company_id" and marketplace != "ozon":
                return
            else:
                updated_account[key] = str(value or "")

            normalized_account = _normalize_account(updated_account, index)
            if normalized_account is not None:
                accounts[index] = normalized_account
                self.config = _sync_legacy_sections_from_accounts(self.config)
            return

    def get_accounts(self):
        """Получение списка аккаунтов с поддержкой legacy single-account формата."""
        if "accounts" in self.config:
            return copy.deepcopy(_normalize_accounts(self.config.get("accounts", [])))
        return copy.deepcopy(_synthesize_accounts_from_legacy(self.config))

    def set_accounts(self, accounts):
        """Полная замена списка аккаунтов."""
        self.config["accounts"] = _normalize_accounts(accounts)
        self.config = _sync_legacy_sections_from_accounts(self.config)

    def set_answers(self, templates):
        """Полная замена шаблонов ответов в памяти."""
        self.answers = copy.deepcopy(templates)

    def get_answer_templates(self):
        """Получение шаблонов ответов."""
        return self.answers


# Глобальный экземпляр конфигурации
config = Config()
