import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config as config_module
import secure_storage as secure_storage_module
from utils.answers import AnswerGenerator


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.base_dir = Path(self.temp_dir.name)
        self.settings_dir = self.base_dir / "settings"
        self.settings_dir.mkdir()

        self.config_example_file = self.settings_dir / "config.example.json"
        self.config_local_file = self.settings_dir / "config.local.json"
        self.legacy_config_file = self.settings_dir / "config.json"
        self.answers_example_file = self.settings_dir / "answers.example.json"
        self.answers_local_file = self.settings_dir / "answers.local.json"
        self.answers_file = self.settings_dir / "answers.json"

        patcher = patch.multiple(
            config_module,
            SETTINGS_DIR=self.settings_dir,
            CONFIG_EXAMPLE_FILE=self.config_example_file,
            CONFIG_LOCAL_FILE=self.config_local_file,
            LEGACY_CONFIG_FILE=self.legacy_config_file,
            ANSWERS_EXAMPLE_FILE=self.answers_example_file,
            ANSWERS_LOCAL_FILE=self.answers_local_file,
            ANSWERS_FILE=self.answers_file,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_loads_example_then_overrides_with_local_config(self):
        self.config_example_file.write_text(
            json.dumps(
                {
                    "general": {
                        "check_interval": 15,
                        "min_stars": 4,
                    },
                    "ozon": {
                        "enabled": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        self.config_local_file.write_text(
            json.dumps(
                {
                    "general": {
                        "check_interval": 5,
                    },
                    "ozon": {
                        "api_key": "local-key",
                    },
                }
            ),
            encoding="utf-8",
        )

        cfg = config_module.Config()

        self.assertEqual(cfg.get("general", "check_interval"), 5)
        self.assertEqual(cfg.get("general", "min_stars"), 4)
        self.assertTrue(cfg.get("ozon", "enabled"))
        self.assertEqual(cfg.get("ozon", "api_key"), "local-key")

    def test_falls_back_to_legacy_config_when_local_file_missing(self):
        self.legacy_config_file.write_text(
            json.dumps(
                {
                    "wildberries": {
                        "enabled": True,
                        "api_key": "legacy-token",
                    }
                }
            ),
            encoding="utf-8",
        )

        cfg = config_module.Config()

        self.assertTrue(cfg.get("wildberries", "enabled"))
        self.assertEqual(cfg.get("wildberries", "api_key"), "legacy-token")

    def test_save_config_writes_only_local_config_file(self):
        cfg = config_module.Config()
        cfg.set("general", "check_interval", 10)

        cfg.save_config()

        self.assertTrue(self.config_local_file.exists())
        self.assertFalse(self.legacy_config_file.exists())

        saved = json.loads(self.config_local_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["general"]["check_interval"], 10)

    def test_save_answers_writes_only_local_answers_file(self):
        cfg = config_module.Config()
        cfg.set_answers({"5": ["Спасибо!"]})

        cfg.save_answers()

        self.assertTrue(self.answers_local_file.exists())
        self.assertFalse(self.answers_file.exists())

        saved = json.loads(self.answers_local_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["5"], ["Спасибо!"])

    def test_environment_variables_override_secrets(self):
        self.config_local_file.write_text(
            json.dumps(
                {
                    "ozon": {
                        "api_key": "local-ozon",
                        "company_id": "local-company",
                    },
                    "wildberries": {
                        "api_key": "local-wb",
                    },
                }
            ),
            encoding="utf-8",
        )

        with patch.dict(
            "os.environ",
            {
                "MARKETPLACEBOT_OZON_API_KEY": "env-ozon",
                "MARKETPLACEBOT_OZON_COMPANY_ID": "env-company",
                "MARKETPLACEBOT_WB_API_KEY": "env-wb",
            },
            clear=False,
        ):
            cfg = config_module.Config()

        self.assertEqual(cfg.get("ozon", "api_key"), "env-ozon")
        self.assertEqual(cfg.get("ozon", "company_id"), "env-company")
        self.assertEqual(cfg.get("wildberries", "api_key"), "env-wb")

    def test_reads_multi_account_format(self):
        self.config_local_file.write_text(
            json.dumps(
                {
                    "accounts": [
                        {
                            "id": "ozon-main",
                            "name": "Ozon Main",
                            "marketplace": "ozon",
                            "enabled": True,
                            "api_key": "ozon-key-1",
                            "company_id": "company-1",
                        },
                        {
                            "id": "ozon-backup",
                            "name": "Ozon Backup",
                            "marketplace": "ozon",
                            "enabled": False,
                            "api_key": "ozon-key-2",
                            "company_id": "company-2",
                        },
                        {
                            "id": "wb-main",
                            "name": "WB Main",
                            "marketplace": "wildberries",
                            "enabled": True,
                            "api_key": "wb-key-1",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        cfg = config_module.Config()

        accounts = cfg.get_accounts()
        self.assertEqual(len(accounts), 3)
        self.assertEqual(accounts[0]["id"], "ozon-main")
        self.assertEqual(accounts[0]["company_id"], "company-1")
        self.assertEqual(accounts[2]["marketplace"], "wildberries")
        self.assertEqual(accounts[2]["company_id"], "")

        self.assertEqual(cfg.get("ozon", "api_key"), "ozon-key-1")
        self.assertEqual(cfg.get("ozon", "company_id"), "company-1")
        self.assertTrue(cfg.get("ozon", "enabled"))
        self.assertEqual(cfg.get("wildberries", "api_key"), "wb-key-1")
        self.assertTrue(cfg.get("wildberries", "enabled"))

    def test_reads_protected_api_keys_from_local_config(self):
        protected_ozon = secure_storage_module.protect_secret("ozon-protected-key", os_name="posix")
        protected_wb = secure_storage_module.protect_secret("wb-protected-key", os_name="posix")
        protected_account = secure_storage_module.protect_secret("account-protected-key", os_name="posix")
        protected_wb_account = secure_storage_module.protect_secret("wb-account-protected-key", os_name="posix")
        self.config_local_file.write_text(
            json.dumps(
                {
                    "ozon": {
                        "api_key": protected_ozon,
                        "company_id": "company-1",
                    },
                    "wildberries": {
                        "api_key": protected_wb,
                    },
                    "accounts": [
                        {
                            "id": "ozon-main",
                            "name": "Ozon Main",
                            "marketplace": "ozon",
                            "enabled": True,
                            "api_key": protected_account,
                            "company_id": "company-1",
                        },
                        {
                            "id": "wb-main",
                            "name": "WB Main",
                            "marketplace": "wildberries",
                            "enabled": True,
                            "api_key": protected_wb_account,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        cfg = config_module.Config()

        self.assertEqual(cfg.get("ozon", "api_key"), "account-protected-key")
        self.assertEqual(cfg.get("wildberries", "api_key"), "wb-account-protected-key")
        self.assertEqual(cfg.get_accounts()[0]["api_key"], "account-protected-key")
        self.assertEqual(cfg.get_accounts()[1]["api_key"], "wb-account-protected-key")

    def test_reads_protected_legacy_api_keys_without_accounts(self):
        self.config_local_file.write_text(
            json.dumps(
                {
                    "ozon": {
                        "enabled": True,
                        "api_key": secure_storage_module.protect_secret("legacy-ozon-protected", os_name="posix"),
                        "company_id": "legacy-company",
                    },
                    "wildberries": {
                        "enabled": True,
                        "api_key": secure_storage_module.protect_secret("legacy-wb-protected", os_name="posix"),
                    },
                }
            ),
            encoding="utf-8",
        )

        cfg = config_module.Config()

        self.assertEqual(cfg.get("ozon", "api_key"), "legacy-ozon-protected")
        self.assertEqual(cfg.get("wildberries", "api_key"), "legacy-wb-protected")

    def test_get_accounts_synthesizes_from_legacy_single_account_format(self):
        self.config_local_file.write_text(
            json.dumps(
                {
                    "ozon": {
                        "enabled": True,
                        "api_key": "legacy-ozon-key",
                        "company_id": "legacy-company",
                    },
                    "wildberries": {
                        "enabled": False,
                        "api_key": "legacy-wb-key",
                    },
                }
            ),
            encoding="utf-8",
        )

        cfg = config_module.Config()

        self.assertEqual(
            cfg.get_accounts(),
            [
                {
                    "id": "ozon-1",
                    "name": "Ozon",
                    "marketplace": "ozon",
                    "enabled": True,
                    "api_key": "legacy-ozon-key",
                    "company_id": "legacy-company",
                },
                {
                    "id": "wildberries-1",
                    "name": "Wildberries",
                    "marketplace": "wildberries",
                    "enabled": False,
                    "api_key": "legacy-wb-key",
                    "company_id": "",
                },
            ],
        )

    def test_save_config_persists_accounts_and_primary_legacy_sections(self):
        cfg = config_module.Config()
        cfg.set_accounts(
            [
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
                    "enabled": True,
                    "api_key": "wb-key-1",
                },
            ]
        )

        cfg.save_config()

        saved = json.loads(self.config_local_file.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["accounts"]), 2)
        self.assertEqual(saved["accounts"][0]["id"], "ozon-main")
        self.assertEqual(saved["accounts"][1]["id"], "wb-main")
        self.assertNotEqual(saved["accounts"][0]["api_key"], "ozon-key-1")
        self.assertNotEqual(saved["ozon"]["api_key"], "ozon-key-1")
        self.assertEqual(saved["ozon"]["company_id"], "company-1")
        self.assertNotEqual(saved["wildberries"]["api_key"], "wb-key-1")
        self.assertEqual(
            secure_storage_module.unprotect_secret(saved["accounts"][0]["api_key"], os_name="posix"),
            "ozon-key-1",
        )
        self.assertEqual(
            secure_storage_module.unprotect_secret(saved["accounts"][1]["api_key"], os_name="posix"),
            "wb-key-1",
        )
        self.assertEqual(
            secure_storage_module.unprotect_secret(saved["ozon"]["api_key"], os_name="posix"),
            "ozon-key-1",
        )
        self.assertEqual(
            secure_storage_module.unprotect_secret(saved["wildberries"]["api_key"], os_name="posix"),
            "wb-key-1",
        )

    def test_legacy_set_updates_primary_account_when_accounts_exist(self):
        cfg = config_module.Config()
        cfg.set_accounts(
            [
                {
                    "id": "ozon-main",
                    "name": "Ozon Main",
                    "marketplace": "ozon",
                    "enabled": False,
                    "api_key": "ozon-key-1",
                    "company_id": "company-1",
                }
            ]
        )

        cfg.set("ozon", "enabled", True)
        cfg.set("ozon", "api_key", "updated-ozon-key")
        cfg.set("ozon", "company_id", "updated-company")

        accounts = cfg.get_accounts()
        self.assertEqual(accounts[0]["api_key"], "updated-ozon-key")
        self.assertEqual(accounts[0]["company_id"], "updated-company")
        self.assertTrue(accounts[0]["enabled"])
        self.assertEqual(cfg.get("ozon", "api_key"), "updated-ozon-key")

    def test_save_config_writes_protected_legacy_api_keys(self):
        cfg = config_module.Config()
        cfg.set("ozon", "api_key", "legacy-ozon-secret")
        cfg.set("wildberries", "api_key", "legacy-wb-secret")

        cfg.save_config()

        saved = json.loads(self.config_local_file.read_text(encoding="utf-8"))
        self.assertNotEqual(saved["ozon"]["api_key"], "legacy-ozon-secret")
        self.assertNotEqual(saved["wildberries"]["api_key"], "legacy-wb-secret")
        self.assertEqual(
            secure_storage_module.unprotect_secret(saved["ozon"]["api_key"], os_name="posix"),
            "legacy-ozon-secret",
        )
        self.assertEqual(
            secure_storage_module.unprotect_secret(saved["wildberries"]["api_key"], os_name="posix"),
            "legacy-wb-secret",
        )

    def test_windows_save_config_uses_dpapi_envelope_on_success(self):
        cfg = config_module.Config()
        cfg.set("ozon", "api_key", "windows-ozon-secret")

        with patch.object(secure_storage_module.os, "name", "nt"), \
             patch.object(secure_storage_module, "_dpapi_encrypt_bytes", return_value=b"ciphertext"):
            cfg.save_config()

        saved = json.loads(self.config_local_file.read_text(encoding="utf-8"))
        self.assertEqual(
            secure_storage_module.get_protected_secret_scheme(saved["ozon"]["api_key"]),
            secure_storage_module.WINDOWS_SCHEME,
        )

    def test_windows_save_config_fails_closed_when_dpapi_protection_fails(self):
        cfg = config_module.Config()
        cfg.set("ozon", "api_key", "windows-ozon-secret")

        with patch.object(secure_storage_module.os, "name", "nt"), \
             patch.object(
                 secure_storage_module,
                 "_dpapi_encrypt_bytes",
                 side_effect=secure_storage_module.SecretStorageError("dpapi unavailable"),
             ):
            with self.assertRaisesRegex(
                secure_storage_module.SecretStorageError,
                "Не удалось защитить ozon.api_key",
            ):
                cfg.save_config()

        self.assertFalse(self.config_local_file.exists())

    def test_decrypt_error_does_not_crash_config_load(self):
        self.config_local_file.write_text(
            json.dumps(
                {
                    "ozon": {
                        "api_key": "marketplacebot-secure:v1:unknown:not-base64",
                        "company_id": "company-1",
                    }
                }
            ),
            encoding="utf-8",
        )

        with patch.object(config_module, "_log_warning") as log_warning:
            cfg = config_module.Config()

        self.assertEqual(cfg.get("ozon", "api_key"), "")
        log_warning.assert_called()


class AnswerGeneratorTests(unittest.TestCase):
    def test_generate_uses_latest_templates_from_config(self):
        original_answers = config_module.config.answers
        self.addCleanup(setattr, config_module.config, "answers", original_answers)

        config_module.config.answers = {
            "greetings": [],
            "gratitude": [],
            "gratitude_no_comment": ["Новый текст благодарности"],
            "apologies": [],
            "examination": [],
            "main": [],
            "recommendations": [],
            "goodbye": ["Пока"],
            "5": ["Новый текст"],
            "4": [],
            "3": [],
            "3_no_comment": [],
            "2": [],
            "1": [],
            "0": [],
            "stop_words": [],
        }

        generator = AnswerGenerator()
        generator.templates = {
            "greetings": [],
            "gratitude": [],
            "gratitude_no_comment": ["Старый текст благодарности"],
            "apologies": [],
            "examination": [],
            "main": [],
            "recommendations": [],
            "goodbye": ["Пока"],
            "5": ["Старый текст"],
            "4": [],
            "3": [],
            "3_no_comment": [],
            "2": [],
            "1": [],
            "0": [],
            "stop_words": [],
        }

        with patch("utils.answers.random.random", return_value=1.0):
            answer = generator.generate(5, has_comment=False)

        self.assertIn("Новый текст", answer)
        self.assertIn("Новый текст благодарности", answer)
        self.assertNotIn("Старый текст", answer)


if __name__ == "__main__":
    unittest.main()
