import tempfile
import unittest
from pathlib import Path

import runtime_paths as runtime_paths_module
from utils.review_state import ReviewStateStore, STATE_FILE


class ReviewStateStoreTests(unittest.TestCase):
    def test_default_state_file_uses_runtime_aware_settings_dir(self):
        self.assertEqual(STATE_FILE.parent, runtime_paths_module.RUNTIME_PATHS.settings_dir)

    def test_reload_preserves_processed_reviews_from_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "review_state.json"
            store = ReviewStateStore(state_file=state_file)
            self.assertTrue(store.mark_processed("ozon", "acc-1", "r1", processed_at="2026-04-09T10:00:00+00:00"))

            reloaded_store = ReviewStateStore(state_file=state_file)
            self.assertTrue(reloaded_store.has_processed("ozon", "acc-1", "r1"))

    def test_pruning_keeps_only_newest_entries_per_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "review_state.json"
            store = ReviewStateStore(state_file=state_file, max_entries_per_account=2)

            store.mark_processed("ozon", "acc-1", "r1", processed_at="2026-04-09T10:00:00+00:00")
            store.mark_processed("ozon", "acc-1", "r2", processed_at="2026-04-09T10:01:00+00:00")
            store.mark_processed("ozon", "acc-1", "r3", processed_at="2026-04-09T10:02:00+00:00")

            reviews = store.get_account_reviews("ozon", "acc-1")
            self.assertEqual(set(reviews.keys()), {"r2", "r3"})
            self.assertFalse(store.has_processed("ozon", "acc-1", "r1"))
            self.assertTrue(store.has_processed("ozon", "acc-1", "r3"))


if __name__ == "__main__":
    unittest.main()
