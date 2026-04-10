import tempfile
import unittest
from pathlib import Path

from runtime_assets import ensure_bundled_example_assets


class RuntimeAssetsTests(unittest.TestCase):
    def test_copies_missing_example_assets_to_runtime_settings_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            bundled_settings_dir = root_dir / "bundle" / "settings"
            runtime_settings_dir = root_dir / "runtime" / "settings"
            bundled_settings_dir.mkdir(parents=True)

            (bundled_settings_dir / "config.example.json").write_text("{}", encoding="utf-8")
            (bundled_settings_dir / "answers.example.json").write_text('{"5":["Спасибо!"]}', encoding="utf-8")

            copied_files = ensure_bundled_example_assets(runtime_settings_dir, bundled_settings_dir)

            self.assertEqual(
                {path.name for path in copied_files},
                {"config.example.json", "answers.example.json"},
            )
            self.assertEqual((runtime_settings_dir / "config.example.json").read_text(encoding="utf-8"), "{}")
            self.assertIn("Спасибо", (runtime_settings_dir / "answers.example.json").read_text(encoding="utf-8"))

    def test_does_not_overwrite_existing_runtime_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            bundled_settings_dir = root_dir / "bundle" / "settings"
            runtime_settings_dir = root_dir / "runtime" / "settings"
            bundled_settings_dir.mkdir(parents=True)
            runtime_settings_dir.mkdir(parents=True)

            (bundled_settings_dir / "config.example.json").write_text('{"general":{"check_interval":60}}', encoding="utf-8")
            (runtime_settings_dir / "config.example.json").write_text('{"general":{"check_interval":5}}', encoding="utf-8")

            copied_files = ensure_bundled_example_assets(runtime_settings_dir, bundled_settings_dir)

            self.assertEqual(copied_files, [])
            self.assertIn("5", (runtime_settings_dir / "config.example.json").read_text(encoding="utf-8"))

    def test_noop_when_bundle_and_runtime_directories_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_dir = Path(temp_dir) / "settings"
            settings_dir.mkdir(parents=True)
            (settings_dir / "config.example.json").write_text("{}", encoding="utf-8")

            copied_files = ensure_bundled_example_assets(settings_dir, settings_dir)

            self.assertEqual(copied_files, [])


if __name__ == "__main__":
    unittest.main()
