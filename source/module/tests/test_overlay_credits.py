import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hotkeys_windows import OverlayKeyState
from credits_static import get_special_thanks, SPECIAL_THANKS

class OverlayKeyStateTests(unittest.TestCase):
    def test_navigation_only_when_active(self):
        state = OverlayKeyState()
        self.assertEqual(state.handle(0x25, True, False), (False, False))
        self.assertEqual(state.handle(0x25, True, True), (True, True))
        self.assertEqual(state.handle(0x25, True, True), (True, False))
        self.assertEqual(state.handle(0x25, False, True), (True, False))
        self.assertEqual(state.handle(0x25, True, False), (False, False))

    def test_keyup_captured_after_overlay_closes(self):
        state = OverlayKeyState()
        self.assertEqual(state.handle(0x0D, True, True), (True, True))
        self.assertEqual(state.handle(0x0D, False, False), (True, False))

    def test_unrelated_keys_and_modified_shortcuts_pass_through(self):
        state = OverlayKeyState()
        for vk in (0x46, 0x51, 0x70):
            self.assertEqual(state.handle(vk, True, True), (False, False))
        self.assertEqual(state.handle(0x25, True, True, modified=True), (False, False))

    def test_numeric_selector_and_numpad_supported(self):
        state = OverlayKeyState()
        for vk in (*range(0x31, 0x37), *range(0x61, 0x67)):
            self.assertEqual(state.handle(vk, True, True), (True, True))
            self.assertEqual(state.handle(vk, False, True), (True, False))

    def test_modifier_passthrough_even_when_overlay_open(self):
        state = OverlayKeyState()
        self.assertEqual(state.handle(0x1B, True, True, modified=True), (False, False))


class SpecialThanksTests(unittest.TestCase):
    def test_no_external_ini(self):
        self.assertFalse((ROOT / 'credits.ini').exists())
        self.assertFalse((ROOT / 'credits_loader.py').exists())
        self.assertEqual(get_special_thanks(), tuple((k, v) for k,v in SPECIAL_THANKS if k.strip() and v.strip()))

    def test_no_credit_editor_or_ini_launcher(self):
        app = (ROOT / 'app.py').read_text(encoding='utf8')
        self.assertIn('get_special_thanks()', app)
        self.assertIn('self.special_list', app)
        self.assertNotIn('_open_credits_ini', app)
        self.assertNotIn('credits.ini 열기', app)
        build = (ROOT.parent / 'build_windows.bat').read_text(encoding='utf8')
        self.assertNotIn('copy /Y "credits.ini"', build)

if __name__ == '__main__':
    unittest.main()
