import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hotkeys_windows import CapsQState, HotkeyBinding, key_vk, KEY_LABELS, MOD_CONTROL, MOD_ALT, MOD_SHIFT

class CustomShortcutTests(unittest.TestCase):
    def test_capslock_custom_letter(self):
        state = CapsQState(key_vk('E'))
        self.assertEqual(state.handle(0x14, True), (True, False, False))
        self.assertEqual(state.handle(ord('E'), True), (True, True, False))
        self.assertEqual(state.handle(ord('E'), True), (True, False, False))
        self.assertEqual(state.handle(ord('E'), False), (True, False, False))
        self.assertEqual(state.handle(0x14, False), (True, False, False))

    def test_capslock_custom_digit(self):
        state = CapsQState(key_vk('2'))
        state.handle(0x14, True)
        self.assertTrue(state.handle(ord('2'), True)[1])

    def test_capslock_custom_function_key(self):
        state = CapsQState(key_vk('F9'))
        state.handle(0x14, True)
        self.assertTrue(state.handle(0x78, True)[1])

    def test_capslock_alone(self):
        state = CapsQState(key_vk('Y'))
        state.handle(0x14, True)
        self.assertEqual(state.handle(0x14, False), (True, False, True))

    def test_native_modifier_masks(self):
        self.assertEqual(HotkeyBinding('ctrl_shift', 'D').modifiers, MOD_CONTROL | MOD_SHIFT)
        self.assertEqual(HotkeyBinding('ctrl_alt', 'F12').modifiers, MOD_CONTROL | MOD_ALT)

    def test_binding_labels(self):
        self.assertEqual(HotkeyBinding().title, 'CapsLock + Q')
        self.assertEqual(HotkeyBinding('ctrl_shift', '3').title, 'Ctrl + Shift + 3')

    def test_invalid_binding(self):
        for mode, key in [('caps','?'), ('bad','Q'), ('ctrl_shift','F13')]:
            with self.assertRaises(ValueError):
                HotkeyBinding(mode, key)

    def test_keys(self):
        self.assertIn('Q', KEY_LABELS)
        self.assertEqual(key_vk('F12'), 0x7B)

if __name__ == '__main__':
    unittest.main()
