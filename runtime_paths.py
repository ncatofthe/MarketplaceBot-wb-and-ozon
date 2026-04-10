"""
Runtime-aware пути приложения.
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple


APP_NAME = "MarketplaceBot"
BASE_DIR = Path(__file__).resolve().parent


class RuntimePaths(NamedTuple):
    """Набор вычисленных runtime-директорий приложения."""

    base_dir: Path
    settings_dir: Path
    logs_dir: Path
    mode: str


def _safe_home_dir():
    """Получение домашней директории с безопасным fallback."""
    try:
        return Path.home()
    except Exception:
        return None


def _normalize_path(path_value):
    """Нормализация пути из env/config без строгого resolve."""
    return Path(path_value).expanduser()


def _default_windows_settings_dir(env, home_dir):
    """Путь к пользовательским настройкам в frozen Windows режиме."""
    appdata = env.get("APPDATA")
    if appdata:
        return _normalize_path(appdata) / APP_NAME / "settings"
    if home_dir is not None:
        return home_dir / "AppData" / "Roaming" / APP_NAME / "settings"
    return Path(tempfile.gettempdir()) / APP_NAME / "settings"


def _default_windows_logs_dir(env, home_dir):
    """Путь к пользовательским логам в frozen Windows режиме."""
    local_appdata = env.get("LOCALAPPDATA")
    if local_appdata:
        return _normalize_path(local_appdata) / APP_NAME / "logs"
    if home_dir is not None:
        return home_dir / "AppData" / "Local" / APP_NAME / "logs"
    return Path(tempfile.gettempdir()) / APP_NAME / "logs"


def resolve_runtime_paths(base_dir=None, env=None, frozen=None, os_name=None, home_dir=None):
    """Вычисляет директории приложения для текущего runtime-режима."""
    env = os.environ if env is None else env
    base_dir = Path(BASE_DIR if base_dir is None else base_dir).resolve()
    frozen = bool(getattr(sys, "frozen", False)) if frozen is None else bool(frozen)
    os_name = os.name if os_name is None else os_name
    home_dir = _safe_home_dir() if home_dir is None else Path(home_dir)

    settings_override = env.get("MARKETPLACEBOT_SETTINGS_DIR")
    logs_override = env.get("MARKETPLACEBOT_LOGS_DIR")

    if settings_override:
        settings_dir = _normalize_path(settings_override)
    elif frozen and os_name == "nt":
        settings_dir = _default_windows_settings_dir(env, home_dir)
    else:
        settings_dir = base_dir / "settings"

    if logs_override:
        logs_dir = _normalize_path(logs_override)
    elif frozen and os_name == "nt":
        logs_dir = _default_windows_logs_dir(env, home_dir)
    else:
        logs_dir = base_dir / "logs"

    settings_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    mode = "frozen-windows" if frozen and os_name == "nt" else "source"
    return RuntimePaths(
        base_dir=base_dir,
        settings_dir=settings_dir,
        logs_dir=logs_dir,
        mode=mode,
    )


RUNTIME_PATHS = resolve_runtime_paths()


def get_runtime_paths():
    """Возвращает уже вычисленные runtime-пути."""
    return RUNTIME_PATHS
