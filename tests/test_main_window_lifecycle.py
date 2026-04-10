import sys
import types
import unittest
from importlib import util
from pathlib import Path
from unittest import mock


MAIN_WINDOW_PATH = Path(__file__).resolve().parents[1] / "gui" / "main_window.py"

fake_bots_module = types.ModuleType("bots")
fake_bots_module.BotManager = type("ImportedBotManager", (), {})
previous_bots_module = sys.modules.get("bots")
sys.modules["bots"] = fake_bots_module
try:
    SPEC = util.spec_from_file_location("test_main_window_module", MAIN_WINDOW_PATH)
    MAIN_WINDOW_MODULE = util.module_from_spec(SPEC)
    assert SPEC.loader is not None
    SPEC.loader.exec_module(MAIN_WINDOW_MODULE)
finally:
    if previous_bots_module is None:
        del sys.modules["bots"]
    else:
        sys.modules["bots"] = previous_bots_module

MainWindow = MAIN_WINDOW_MODULE.MainWindow


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self):
        self.state = {}
        self.bindings = {}

    def config(self, **kwargs):
        self.state.update(kwargs)

    configure = config

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def state(self, states):
        self.state["state_list"] = list(states)


class FakeLabel(FakeWidget):
    pass


class FakeEntry(FakeWidget):
    def __init__(self, show="*"):
        super().__init__()
        self.generated_events = []
        self.selection = None
        self.cursor = None
        self.focused = False
        self.state["show"] = show

    def event_generate(self, event_name):
        self.generated_events.append(event_name)

    def focus_set(self):
        self.focused = True

    def selection_range(self, start, end):
        self.selection = (start, end)

    def icursor(self, index):
        self.cursor = index


class FakeMenu:
    def __init__(self):
        self.commands = []
        self.popup_calls = []
        self.released = False

    def add_command(self, label, command):
        self.commands.append({"label": label, "command": command})

    def add_separator(self):
        self.commands.append({"separator": True})

    def tk_popup(self, x_root, y_root):
        self.popup_calls.append((x_root, y_root))

    def grab_release(self):
        self.released = True


class FakeText:
    def __init__(self):
        self.content = ""
        self.state = {}

    def config(self, **kwargs):
        self.state.update(kwargs)

    configure = config

    def delete(self, *_args):
        self.content = ""

    def insert(self, *_args):
        self.content += _args[-1]

    def get(self, *_args):
        return self.content


class FakeTreeview:
    def __init__(self):
        self.items = {}
        self.selected = []
        self.focused = None

    def get_children(self):
        return list(self.items.keys())

    def delete(self, item_id):
        self.items.pop(item_id, None)
        if item_id in self.selected:
            self.selected.remove(item_id)

    def insert(self, _parent, _index, iid, values):
        self.items[str(iid)] = {"values": values}

    def selection(self):
        return tuple(self.selected)

    def selection_set(self, item_id):
        self.selected = [str(item_id)]

    def focus(self, item_id):
        self.focused = str(item_id)


class FakeRoot:
    def after(self, _delay, callback):
        callback()

    def destroy(self):
        self.destroyed = True


class FakeBotManager:
    def __init__(self):
        self.bots = {}
        self.statuses = {}
        self.start_all_enabled_result = {}
        self.stop_all_result = {}
        self.start_all_enabled_calls = 0
        self.stop_all_calls = 0

    def get_statuses(self):
        return {key: dict(value) for key, value in self.statuses.items()}

    def start_all_enabled(self):
        self.start_all_enabled_calls += 1
        return dict(self.start_all_enabled_result)

    def stop_all(self):
        self.stop_all_calls += 1
        return dict(self.stop_all_result)


class MainWindowGuiTests(unittest.TestCase):
    def _make_window(self):
        window = MainWindow.__new__(MainWindow)
        window.root = FakeRoot()
        window.bot_manager = FakeBotManager()
        window.accounts = []
        window.selected_account_index = None
        window.entry_context_menu = None
        window._entry_context_widget = None

        window.accounts_tree = FakeTreeview()
        window.accounts_empty_label = FakeLabel()
        window.account_lock_label = FakeLabel()
        window.add_account_button = FakeWidget()
        window.save_account_button = FakeWidget()
        window.delete_account_button = FakeWidget()

        window.account_name_var = FakeVar("")
        window.account_marketplace_var = FakeVar("ozon")
        window.account_enabled_var = FakeVar(False)
        window.account_api_key_var = FakeVar("")
        window.account_api_key_visible = FakeVar(False)
        window.account_company_id_var = FakeVar("")

        window.account_name_entry = FakeEntry(show="")
        window.account_marketplace_combo = FakeWidget()
        window.account_enabled_checkbutton = FakeWidget()
        window.account_api_key_entry = FakeEntry(show="*")
        window.account_company_id_entry = FakeEntry(show="")
        window.account_company_id_label = FakeLabel()
        window.account_company_id_hint_label = FakeLabel()

        window.check_interval = FakeVar(60)
        window.min_stars = FakeVar(1)
        window.max_answers = FakeVar(-1)
        window.short_sleep = FakeVar(0.5)

        window.templates_text = FakeText()
        window.status_text = FakeText()
        window.logs_text = FakeText()
        return window

    def test_load_config_reads_accounts_from_config(self):
        window = self._make_window()
        accounts = [
            {
                "id": "ozon-1",
                "name": "Ozon Main",
                "marketplace": "ozon",
                "enabled": True,
                "api_key": "ozon-secret",
                "company_id": "123",
            },
            {
                "id": "wb-1",
                "name": "WB Shop",
                "marketplace": "wildberries",
                "enabled": False,
                "api_key": "wb-secret",
                "company_id": "",
            },
        ]

        def config_get(section, key=None):
            if section == "general":
                return {
                    "check_interval": 15,
                    "min_stars": 4,
                    "max_answers_per_run": 20,
                    "short_sleep": 0.25,
                }
            return {}

        with mock.patch.object(MAIN_WINDOW_MODULE.config, "get_accounts", return_value=accounts), \
             mock.patch.object(MAIN_WINDOW_MODULE.config, "get", side_effect=config_get), \
             mock.patch.object(MAIN_WINDOW_MODULE.config, "get_answer_templates", return_value={"greetings": []}):
            window._load_config()

        self.assertEqual(window.accounts, accounts)
        self.assertEqual(set(window.accounts_tree.items.keys()), {"ozon-1", "wb-1"})
        self.assertEqual(window.selected_account_index, 0)
        self.assertEqual(window.account_name_var.get(), "Ozon Main")
        self.assertEqual(window.check_interval.get(), 15)

    def test_save_settings_calls_set_accounts_and_general_settings(self):
        window = self._make_window()
        window.accounts = [
            {
                "id": "ozon-1",
                "name": "Ozon Main",
                "marketplace": "ozon",
                "enabled": False,
                "api_key": "",
                "company_id": "",
            }
        ]
        window.selected_account_index = 0
        window.account_name_var.set("Ozon Updated")
        window.account_marketplace_var.set("ozon")
        window.account_enabled_var.set(True)
        window.account_api_key_var.set("new-secret")
        window.account_company_id_var.set("company-777")
        window.check_interval.set(30)
        window.min_stars.set(3)
        window.max_answers.set(10)
        window.short_sleep.set(1.5)

        saved_accounts = [
            {
                "id": "ozon-1",
                "name": "Ozon Updated",
                "marketplace": "ozon",
                "enabled": True,
                "api_key": "new-secret",
                "company_id": "company-777",
            }
        ]

        with mock.patch.object(MAIN_WINDOW_MODULE.config, "set_accounts") as set_accounts, \
             mock.patch.object(MAIN_WINDOW_MODULE.config, "set") as config_set, \
             mock.patch.object(MAIN_WINDOW_MODULE.config, "save_config") as save_config, \
             mock.patch.object(MAIN_WINDOW_MODULE.config, "get_accounts", return_value=saved_accounts):
            result = window._save_settings(show_message=False)

        self.assertTrue(result)
        set_accounts.assert_called_once_with(saved_accounts)
        self.assertEqual(
            config_set.call_args_list,
            [
                mock.call("general", "check_interval", 30),
                mock.call("general", "min_stars", 3),
                mock.call("general", "max_answers_per_run", 10),
                mock.call("general", "short_sleep", 1.5),
            ],
        )
        save_config.assert_called_once()

    def test_marketplace_switch_disables_company_id_for_wildberries(self):
        window = self._make_window()

        window.account_marketplace_var.set("wildberries")
        window._update_company_id_state()
        self.assertEqual(window.account_company_id_entry.state["state"], "disabled")

        window.account_marketplace_var.set("ozon")
        window._update_company_id_state()
        self.assertEqual(window.account_company_id_entry.state["state"], "normal")

    def test_start_bots_uses_bot_manager_start_all_enabled(self):
        window = self._make_window()
        accounts = [
            {
                "id": "wb-1",
                "name": "WB Shop",
                "marketplace": "wildberries",
                "enabled": True,
                "api_key": "wb-secret",
                "company_id": "",
            }
        ]
        window.accounts = accounts
        window.bot_manager.start_all_enabled_result = {"wb-1": True}
        window.bot_manager.statuses = {}

        with mock.patch.object(window, "_save_settings", return_value=True) as save_settings, \
             mock.patch.object(MAIN_WINDOW_MODULE.config, "get_accounts", return_value=accounts), \
             mock.patch.object(MAIN_WINDOW_MODULE.messagebox, "showinfo") as showinfo:
            window._start_bots()

        save_settings.assert_called_once_with(show_message=False)
        self.assertEqual(window.bot_manager.start_all_enabled_calls, 1)
        showinfo.assert_called_once()

    def test_stop_bots_uses_bot_manager_stop_all(self):
        window = self._make_window()
        window.bot_manager.stop_all_result = {"wb-1": True}
        window.bot_manager.statuses = {
            "wb-1": {
                "account_id": "wb-1",
                "account_name": "WB Shop",
                "marketplace": "wildberries",
                "account_enabled": True,
                "running": False,
                "stopping": False,
            }
        }

        with mock.patch.object(MAIN_WINDOW_MODULE.messagebox, "showinfo") as showinfo:
            window._stop_bots(show_message=True)

        self.assertEqual(window.bot_manager.stop_all_calls, 1)
        showinfo.assert_called_once()

    def test_account_changes_blocked_when_bots_are_active(self):
        window = self._make_window()
        window.accounts = [
            {
                "id": "ozon-1",
                "name": "Ozon Main",
                "marketplace": "ozon",
                "enabled": True,
                "api_key": "secret",
                "company_id": "123",
            }
        ]
        window.selected_account_index = 0
        window.bot_manager.statuses = {
            "ozon-1": {
                "account_id": "ozon-1",
                "account_name": "Ozon Main",
                "marketplace": "ozon",
                "account_enabled": True,
                "running": True,
                "stopping": False,
            }
        }

        with mock.patch.object(MAIN_WINDOW_MODULE.messagebox, "showwarning") as showwarning:
            result = window._save_settings(show_message=True)
            window._delete_account()

        self.assertFalse(result)
        self.assertEqual(len(window.accounts), 1)
        self.assertGreaterEqual(showwarning.call_count, 2)

    def test_update_status_renders_multiple_accounts_and_idle_accounts(self):
        window = self._make_window()
        window.accounts = [
            {
                "id": "ozon-1",
                "name": "Ozon Main",
                "marketplace": "ozon",
                "enabled": True,
                "api_key": "secret",
                "company_id": "123",
            },
            {
                "id": "wb-1",
                "name": "WB Backup",
                "marketplace": "wildberries",
                "enabled": False,
                "api_key": "",
                "company_id": "",
            },
        ]
        window.bot_manager.statuses = {
            "ozon-1": {
                "account_id": "ozon-1",
                "account_name": "Ozon Main",
                "marketplace": "ozon",
                "account_enabled": True,
                "running": True,
                "stopping": False,
                "found_reviews": 5,
                "processed_reviews": 4,
                "answered_reviews": 3,
                "skipped_reviews": 1,
                "error_count": 0,
                "last_error": None,
                "last_run_started_at": "2026-04-09 10:00:00",
                "last_run_finished_at": "2026-04-09 10:01:00",
                "last_success_at": "2026-04-09 10:01:00",
            }
        }

        window._update_status()

        self.assertIn("Ozon Main (Ozon, включен)", window.status_text.content)
        self.assertIn("WB Backup (Wildberries, выключен)", window.status_text.content)
        self.assertIn("Еще не запускался", window.status_text.content)

    def test_update_status_has_empty_state_when_accounts_absent(self):
        window = self._make_window()

        window._update_status()

        self.assertIn("Аккаунты еще не добавлены", window.status_text.content)


class MainWindowEntryUxTests(unittest.TestCase):
    def _make_window(self):
        window = MainWindow.__new__(MainWindow)
        window.root = object()
        window.entry_context_menu = None
        window._entry_context_widget = None
        return window

    def test_bind_entry_ux_supports_ctrl_v_and_shift_insert(self):
        window = self._make_window()
        entry = FakeEntry()
        window._bind_entry_ux(entry)

        paste_event = types.SimpleNamespace(widget=entry)
        result_ctrl_v = entry.bindings["<Control-v>"](paste_event)
        result_shift_insert = entry.bindings["<Shift-Insert>"](paste_event)

        self.assertEqual(result_ctrl_v, "break")
        self.assertEqual(result_shift_insert, "break")
        self.assertEqual(entry.generated_events, ["<<Paste>>", "<<Paste>>"])

    def test_context_menu_targets_active_entry(self):
        window = self._make_window()
        entry = FakeEntry()
        fake_menu = FakeMenu()
        event = types.SimpleNamespace(widget=entry, x_root=10, y_root=20)

        with mock.patch.object(MAIN_WINDOW_MODULE.tk, "Menu", return_value=fake_menu):
            window._show_entry_context_menu(event)

        self.assertIs(window._entry_context_widget, entry)
        self.assertEqual(fake_menu.popup_calls, [(10, 20)])
        self.assertTrue(fake_menu.released)
        labels = [item["label"] for item in fake_menu.commands if "label" in item]
        self.assertEqual(labels, ["Вырезать", "Копировать", "Вставить", "Выделить всё"])

        paste_command = next(item["command"] for item in fake_menu.commands if item.get("label") == "Вставить")
        paste_command()
        self.assertEqual(entry.generated_events, ["<<Paste>>"])

    def test_toggle_secret_visibility_switches_mask_without_touching_value(self):
        entry = FakeEntry(show="*")
        visibility = FakeVar(False)

        MainWindow._toggle_secret_visibility(entry, visibility)
        self.assertEqual(entry.state["show"], "*")

        visibility.set(True)
        MainWindow._toggle_secret_visibility(entry, visibility)
        self.assertEqual(entry.state["show"], "")

        visibility.set(False)
        MainWindow._toggle_secret_visibility(entry, visibility)
        self.assertEqual(entry.state["show"], "*")
