"""v0.7 logic checks (no Windows, Qt or global hook required)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hotkeys_windows import CapsQState, VK_CAPITAL, VK_Q
from layout_profiles import create_layout, editable_slots, mode_options


class Version07Tests(unittest.TestCase):
    def test_held_caps_repeated_q_never_leaks(self):
        state = CapsQState()
        self.assertEqual(state.handle(VK_CAPITAL, True), (True, False, False))
        self.assertEqual(state.handle(VK_Q, True), (True, True, False))
        self.assertEqual(state.handle(VK_Q, False), (True, False, False))
        self.assertEqual(state.handle(VK_Q, True), (True, False, False))
        self.assertEqual(state.handle(VK_Q, False), (True, False, False))
        self.assertEqual(state.handle(VK_CAPITAL, False), (True, False, False))

    def test_new_shortcut_only_after_caps_release(self):
        state = CapsQState()
        for i in range(3):
            state.handle(VK_CAPITAL, True)
            self.assertTrue(state.handle(VK_Q, True)[1])
            state.handle(VK_Q, False)
            state.handle(VK_CAPITAL, False)

    def test_unsaved_missing_hkl_not_discarded(self):
        current = [create_layout(0x04090409)]
        saved = [{"hkl":"0000000004110411", "mode":"ja_hiragana", "name":"Japanese"}]
        self.assertEqual(editable_slots(saved, current), saved)

    def test_first_run_one_slot(self):
        current = [create_layout(0x04090409), create_layout(0x04110411)]
        self.assertEqual(len(editable_slots([], current)), 1)

    def test_japanese_half_hiragana_never_offered(self):
        self.assertNotIn("ja_hiragana_half", {k for k, _ in mode_options("japanese")})

    def test_theme_does_not_change_structure(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        for needle in ('self.resize(1020, 690)', 'sidebar.setFixedWidth(226)',
                       'QWidget#window { background:#0D0E11; }',
                       'for text in (tr("대시보드"), tr("입력기 슬롯"), tr("일반 설정"), tr("프로그램 정보"),tr(\'사용자 사전\'))'):
            self.assertIn(needle, src)

    def test_main_event_and_console(self):
        code = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('self.quit_requested.emit()', code)
        self.assertIn('RotatingFileHandler(', code)
        runner = (ROOT.parent / "run.bat").read_text(encoding='utf-8')
        self.assertIn('pythonw.exe', runner)
        self.assertIn('start ""', runner)

    def test_special_thanks_from_ini(self):
        code = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('get_special_thanks()', code)
        self.assertNotIn('def _edit_reviewer(', code)


if __name__ == '__main__':
    unittest.main()
