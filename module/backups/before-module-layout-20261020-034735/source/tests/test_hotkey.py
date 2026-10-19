"""Cross-platform unit tests for CapsQState; no hook or Qt required."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hotkeys_windows import CapsQState, VK_CAPITAL, VK_Q


class HotkeyTests(unittest.TestCase):
    def test_caps_plus_q_both_are_swallowed(self):
        state = CapsQState()
        self.assertEqual(state.handle(VK_CAPITAL, True), (True, False, False))
        self.assertEqual(state.handle(VK_Q, True), (True, True, False))
        self.assertEqual(state.handle(VK_Q, False), (True, False, False))
        self.assertEqual(state.handle(VK_CAPITAL, False), (True, False, False))

    def test_repeat_does_not_open_multiple_overlays(self):
        state = CapsQState()
        state.handle(VK_CAPITAL, True)
        self.assertTrue(state.handle(VK_Q, True)[1])
        self.assertFalse(state.handle(VK_Q, True)[1])
        state.handle(VK_CAPITAL, False)
        self.assertEqual(state.handle(VK_Q, False), (True, False, False))

    def test_caps_alone_preserves_capslock(self):
        state = CapsQState()
        self.assertEqual(state.handle(VK_CAPITAL, True), (True, False, False))
        self.assertEqual(state.handle(VK_CAPITAL, False), (True, False, True))

    def test_caps_and_other_key_is_not_hotkey(self):
        state = CapsQState()
        state.handle(VK_CAPITAL, True)
        self.assertEqual(state.handle(0x41, True), (False, False, True))  # A
        self.assertEqual(state.handle(0x41, False), (False, False, False))
        self.assertEqual(state.handle(VK_CAPITAL, False), (True, False, False))

    def test_plain_q_passthrough(self):
        state = CapsQState()
        self.assertEqual(state.handle(VK_Q, True), (False, False, False))
        self.assertEqual(state.handle(VK_Q, False), (False, False, False))

    def test_second_press_after_release(self):
        state = CapsQState()
        for _ in range(2):
            state.handle(VK_CAPITAL, True)
            self.assertTrue(state.handle(VK_Q, True)[1])
            state.handle(VK_Q, False)
            state.handle(VK_CAPITAL, False)


if __name__ == '__main__':
    unittest.main()
