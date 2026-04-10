import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import main as main_module
import runtime_paths as runtime_paths_module
import single_instance as single_instance_module


class SingleInstanceLockTests(unittest.TestCase):
    def test_first_instance_acquires_second_does_not_and_can_reacquire_after_release(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_file = Path(temp_dir) / "test-app.lock"
            lock1 = single_instance_module.SingleInstanceLock(lock_file=lock_file)
            lock2 = single_instance_module.SingleInstanceLock(lock_file=lock_file)
            lock3 = single_instance_module.SingleInstanceLock(lock_file=lock_file)

            try:
                self.assertTrue(lock1.acquire())
                self.assertFalse(lock2.acquire())
                lock1.release()
                self.assertTrue(lock3.acquire())
            finally:
                lock1.release()
                lock2.release()
                lock3.release()

    def test_default_lock_path_uses_runtime_aware_settings_dir(self):
        self.assertEqual(single_instance_module.LOCK_FILE.parent, runtime_paths_module.RUNTIME_PATHS.settings_dir)


class MainStartupFlowTests(unittest.TestCase):
    def test_main_exits_early_when_second_instance_detected(self):
        fake_gui = types.ModuleType("gui")
        fake_gui.run_gui = mock.Mock()
        previous_gui = sys.modules.get("gui")

        with mock.patch.object(main_module.APP_LOCK, "acquire", return_value=False) as acquire, \
             mock.patch.object(main_module.APP_LOCK, "release") as release, \
             mock.patch.object(main_module, "_show_already_running_message") as show_message:
            sys.modules["gui"] = fake_gui
            try:
                result = main_module.main()
            finally:
                if previous_gui is None:
                    del sys.modules["gui"]
                else:
                    sys.modules["gui"] = previous_gui

        self.assertEqual(result, 1)
        acquire.assert_called_once()
        show_message.assert_called_once()
        release.assert_not_called()
        fake_gui.run_gui.assert_not_called()

    def test_main_releases_lock_after_gui_shutdown(self):
        fake_gui = types.ModuleType("gui")
        fake_gui.run_gui = mock.Mock()
        previous_gui = sys.modules.get("gui")

        with mock.patch.object(main_module.APP_LOCK, "acquire", return_value=True) as acquire, \
             mock.patch.object(main_module.APP_LOCK, "release") as release:
            sys.modules["gui"] = fake_gui
            try:
                result = main_module.main()
            finally:
                if previous_gui is None:
                    del sys.modules["gui"]
                else:
                    sys.modules["gui"] = previous_gui

        self.assertEqual(result, 0)
        acquire.assert_called_once()
        fake_gui.run_gui.assert_called_once()
        release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
