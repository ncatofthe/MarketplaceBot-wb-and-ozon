import tempfile
import unittest
from pathlib import Path

import config as config_module
import runtime_paths as runtime_paths_module
from utils import logger as logger_instance


LOGGER_MODULE = __import__("utils.logger", fromlist=["Logger"])


class RuntimePathsTests(unittest.TestCase):
    def test_source_mode_uses_local_project_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "project"
            base_dir.mkdir()
            resolved_base_dir = base_dir.resolve()

            paths = runtime_paths_module.resolve_runtime_paths(
                base_dir=base_dir,
                env={},
                frozen=False,
                os_name="posix",
                home_dir=base_dir / "home",
            )

            self.assertEqual(paths.mode, "source")
            self.assertEqual(paths.settings_dir, resolved_base_dir / "settings")
            self.assertEqual(paths.logs_dir, resolved_base_dir / "logs")
            self.assertTrue(paths.settings_dir.exists())
            self.assertTrue(paths.logs_dir.exists())

    def test_frozen_windows_uses_appdata_and_localappdata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            appdata_dir = root_dir / "AppData" / "Roaming"
            local_appdata_dir = root_dir / "AppData" / "Local"

            paths = runtime_paths_module.resolve_runtime_paths(
                base_dir=root_dir / "bundle",
                env={
                    "APPDATA": str(appdata_dir),
                    "LOCALAPPDATA": str(local_appdata_dir),
                },
                frozen=True,
                os_name="nt",
                home_dir=root_dir / "User",
            )

            self.assertEqual(paths.mode, "frozen-windows")
            self.assertEqual(paths.settings_dir, appdata_dir / "MarketplaceBot" / "settings")
            self.assertEqual(paths.logs_dir, local_appdata_dir / "MarketplaceBot" / "logs")
            self.assertTrue(paths.settings_dir.exists())
            self.assertTrue(paths.logs_dir.exists())

    def test_frozen_windows_falls_back_to_home_layout_when_env_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            home_dir = root_dir / "User"

            paths = runtime_paths_module.resolve_runtime_paths(
                base_dir=root_dir / "bundle",
                env={},
                frozen=True,
                os_name="nt",
                home_dir=home_dir,
            )

            self.assertEqual(paths.settings_dir, home_dir / "AppData" / "Roaming" / "MarketplaceBot" / "settings")
            self.assertEqual(paths.logs_dir, home_dir / "AppData" / "Local" / "MarketplaceBot" / "logs")
            self.assertTrue(paths.settings_dir.exists())
            self.assertTrue(paths.logs_dir.exists())

    def test_env_overrides_take_priority_over_runtime_detection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            custom_settings_dir = root_dir / "custom-settings"
            custom_logs_dir = root_dir / "custom-logs"

            paths = runtime_paths_module.resolve_runtime_paths(
                base_dir=root_dir / "bundle",
                env={
                    "MARKETPLACEBOT_SETTINGS_DIR": str(custom_settings_dir),
                    "MARKETPLACEBOT_LOGS_DIR": str(custom_logs_dir),
                    "APPDATA": str(root_dir / "ignored-roaming"),
                    "LOCALAPPDATA": str(root_dir / "ignored-local"),
                },
                frozen=True,
                os_name="nt",
                home_dir=root_dir / "User",
            )

            self.assertEqual(paths.settings_dir, custom_settings_dir)
            self.assertEqual(paths.logs_dir, custom_logs_dir)
            self.assertTrue(paths.settings_dir.exists())
            self.assertTrue(paths.logs_dir.exists())

    def test_config_and_logger_use_shared_runtime_paths(self):
        self.assertEqual(config_module.BASE_DIR, runtime_paths_module.RUNTIME_PATHS.base_dir)
        self.assertEqual(config_module.SETTINGS_DIR, runtime_paths_module.RUNTIME_PATHS.settings_dir)
        self.assertEqual(config_module.LOGS_DIR, runtime_paths_module.RUNTIME_PATHS.logs_dir)
        self.assertEqual(LOGGER_MODULE.BASE_DIR, runtime_paths_module.RUNTIME_PATHS.base_dir)
        self.assertEqual(LOGGER_MODULE.LOGS_DIR, runtime_paths_module.RUNTIME_PATHS.logs_dir)
        self.assertIsNotNone(logger_instance)


if __name__ == "__main__":
    unittest.main()
