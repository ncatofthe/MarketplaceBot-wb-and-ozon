"""
Bootstrap bundled runtime assets into the user settings directory.
"""
import shutil
from pathlib import Path


EXAMPLE_ASSET_NAMES = (
    "config.example.json",
    "answers.example.json",
)


def ensure_bundled_example_assets(settings_dir, bundled_settings_dir, asset_names=EXAMPLE_ASSET_NAMES):
    """Копирует example assets из bundle в runtime settings dir при первом запуске."""
    settings_dir = Path(settings_dir)
    bundled_settings_dir = Path(bundled_settings_dir)
    settings_dir.mkdir(parents=True, exist_ok=True)

    try:
        if settings_dir.resolve() == bundled_settings_dir.resolve():
            return []
    except OSError:
        pass

    copied_files = []
    for asset_name in asset_names:
        source = bundled_settings_dir / asset_name
        target = settings_dir / asset_name
        if target.exists() or not source.exists():
            continue
        shutil.copy2(source, target)
        copied_files.append(target)

    return copied_files
