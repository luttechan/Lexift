"""Lexift 0.7.4 regression checks: universal font and native first-run picker."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from native_language_dialog import NativeDialogUnavailable, language_choices, choose_ui_language
from i18n import LANGUAGES

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'app.py').read_text(encoding='utf-8')


class V074Tests(unittest.TestCase):
    def test_native_language_choices_are_nine_and_stable(self):
        choices = language_choices(LANGUAGES)
        self.assertEqual(len(choices), 9)
        self.assertEqual([item[1] for item in choices], [code for code, _ in LANGUAGES])
        self.assertEqual(len(set(item[0] for item in choices)), len(choices))
        self.assertEqual(choices[0], (100, 'ko', '한국어'))

    def test_language_choice_is_windows_only(self):
        with patch.object(sys, 'platform', 'linux'):
            with self.assertRaises(NativeDialogUnavailable):
                choose_ui_language(LANGUAGES)

    def test_malgun_gothic_is_qt_root_font(self):
        self.assertIn('font-family:"Malgun Gothic";', SOURCE)
        self.assertIn('font = QFont(family, 10)', SOURCE)
        self.assertIn('app.setFont(font)', SOURCE)
        self.assertNotIn('for family in ("Pretendard"', SOURCE)

    def test_first_run_language_precedes_controller(self):
        start = SOURCE.index('def main() -> int:')
        startup = SOURCE[start:]
        self.assertLess(startup.index('choose_ui_language(LANGUAGES'),
                        startup.index('managers["main"] = LexiftController(qt)'))
        self.assertLess(startup.index("prefs.setValue('general/ui_language', chosen)"),
                        startup.index('managers["main"] = LexiftController(qt)'))
        self.assertIn('setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)', SOURCE)

    def test_runtime_language_switch_preserved(self):
        self.assertIn('def change_language(self, code: str) -> None:', SOURCE)
        self.assertIn('self.store.setValue(\'general/ui_language\', code)', SOURCE)
        self.assertIn('class Overlay(QDialog)', SOURCE)
        self.assertIn('class LanguagePicker(QDialog)', SOURCE)


if __name__ == '__main__':
    unittest.main()
