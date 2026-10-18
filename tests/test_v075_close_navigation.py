import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grid_navigation import move_selection
from i18n import CATALOG, LANGUAGES


class SpatialNavigation(unittest.TestCase):
    def test_four_slot_ragged_row(self):
        # 1 2 3 / 4 ; Right from 3 goes to 4, Down from 3 goes to 4.
        self.assertEqual(move_selection(2, 4, 3, "right"), 3)
        self.assertEqual(move_selection(2, 4, 3, "down"), 3)
        self.assertEqual(move_selection(0, 4, 3, "down"), 3)
        self.assertEqual(move_selection(3, 4, 3, "up"), 0)
    def test_full_grid(self):
        # 1 2 3 / 4 5 6 ; Down from 3 goes to 6.
        self.assertEqual(move_selection(2, 6, 3, "down"), 5)
        self.assertEqual(move_selection(5, 6, 3, "up"), 2)
        self.assertEqual(move_selection(2, 6, 3, "right"), 3)
    def test_five_slots_and_vertical_boundaries(self):
        self.assertEqual(move_selection(2, 5, 3, "down"), 4)
        self.assertEqual(move_selection(4, 5, 3, "down"), 4)
        self.assertEqual(move_selection(1, 5, 3, "up"), 1)
    def test_one_two_three_slots(self):
        for n in (1, 2, 3):
            for i in range(n):
                self.assertEqual(move_selection(i, n, n, "down"), i)
                self.assertEqual(move_selection(i, n, n, "up"), i)
    def test_horizontal_wrap(self):
        self.assertEqual(move_selection(3, 4, 3, "right"), 0)
        self.assertEqual(move_selection(0, 4, 3, "left"), 3)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            move_selection(5, 3, 3, "up")
        with self.assertRaises(ValueError):
            move_selection(0, 3, 0, "down")
    def test_close_to_tray_controller_and_ui(self):
        code = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("self.tray_hide_requested.emit()",code)
        self.assertIn("self.window.tray_hide_requested.connect(self.notify_running_in_tray)",code)
        self.assertIn("replacement.tray_hide_requested.connect(self.notify_running_in_tray)",code)
        self.assertIn("self.tray.showMessage(",code)
        self.assertIn('move_selection(self.index, len(self.tiles), self.columns, direction)', code)
    def test_close_notification_localized(self):
        for code, _ in LANGUAGES:
            if code != 'ko':
                self.assertIn('알림 영역에서 계속 실행됩니다.', CATALOG[code])

if __name__ == '__main__':
    unittest.main()
