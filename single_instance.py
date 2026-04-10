"""
Single-instance защита для desktop-приложения.
"""
import atexit
import os
import threading
from pathlib import Path

from runtime_paths import get_runtime_paths


RUNTIME_PATHS = get_runtime_paths()
LOCK_FILE = RUNTIME_PATHS.settings_dir / "marketplacebot.lock"


class SingleInstanceLock:
    """Небольшой cross-platform file lock для одного экземпляра приложения."""

    _process_lock = threading.Lock()
    _held_paths = set()

    def __init__(self, lock_file=None):
        self.lock_file = Path(lock_file or LOCK_FILE)
        self._file_handle = None
        self._acquired = False
        self._atexit_registered = False

    def acquire(self):
        """Пытается захватить single-instance lock."""
        if self._acquired:
            return True

        lock_path = str(self.lock_file)
        with self._process_lock:
            if lock_path in self._held_paths:
                return False

        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        file_handle = open(self.lock_file, "a+b")

        try:
            self._acquire_os_lock(file_handle)
        except OSError:
            file_handle.close()
            return False

        self._write_lock_metadata(file_handle)

        with self._process_lock:
            self._held_paths.add(lock_path)

        self._file_handle = file_handle
        self._acquired = True

        if not self._atexit_registered:
            atexit.register(self.release)
            self._atexit_registered = True

        return True

    def release(self):
        """Освобождает lock и закрывает файл."""
        if not self._acquired or self._file_handle is None:
            return

        try:
            self._release_os_lock(self._file_handle)
        except OSError:
            pass
        finally:
            try:
                self._file_handle.close()
            except OSError:
                pass

            with self._process_lock:
                self._held_paths.discard(str(self.lock_file))

            self._file_handle = None
            self._acquired = False

    def _acquire_os_lock(self, file_handle):
        """Захват OS-level lock без ожидания."""
        if os.name == "nt":
            import msvcrt

            file_handle.seek(0)
            if file_handle.tell() == 0:
                file_handle.write(b"0")
                file_handle.flush()
            file_handle.seek(0)
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            return

        import fcntl

        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _release_os_lock(self, file_handle):
        """Освобождение OS-level lock."""
        if os.name == "nt":
            import msvcrt

            file_handle.seek(0)
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _write_lock_metadata(file_handle):
        """Записывает pid владельца lock для диагностики."""
        try:
            file_handle.seek(0)
            file_handle.truncate()
            file_handle.write(f"{os.getpid()}\n".encode("utf-8"))
            file_handle.flush()
        except OSError:
            pass

    @property
    def is_acquired(self):
        """Текущий статус lock."""
        return self._acquired
