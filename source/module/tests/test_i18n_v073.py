"""Regressions for v0.7.3 offline UI language switching and embedded credits."""
import unittest
from pathlib import Path
from i18n import LANGUAGES, CATALOG, _ROWS, SUPPORTED, set_language, tr, tr_count, tr_hint, tr_notify
from credits_static import get_special_thanks

ROOT=Path(__file__).resolve().parents[1]

class LocaleTests(unittest.TestCase):
    def tearDown(self):
        set_language('ko')

    def test_offered_languages_complete(self):
        self.assertEqual(len(LANGUAGES), len(set(c for c,n in LANGUAGES)))
        self.assertGreaterEqual(len(LANGUAGES), 9)
        for lang in SUPPORTED - {'ko'}:
            self.assertEqual(set(_ROWS), set(_ROWS) & set(CATALOG[lang]))
            self.assertTrue(all(CATALOG[lang].values()))

    def test_language_change_immediate_and_reversible(self):
        set_language('en')
        self.assertEqual(tr('대시보드'), 'Dashboard')
        set_language('ja')
        self.assertEqual(tr('대시보드'), 'ダッシュボード')
        set_language('ko')
        self.assertEqual(tr('대시보드'), '대시보드')

    def test_locale_specific_dynamic_labels(self):
        set_language('fr')
        self.assertIn('3', tr_count(3,'CapsLock + Q'))
        self.assertIn('CapsLock + Q',tr_hint('CapsLock + Q'))
        self.assertIn('CapsLock + Q',tr_notify('CapsLock + Q'))

    def test_reject_unknown_languages(self):
        with self.assertRaises(ValueError):
            set_language('xx_XX')

    def test_embedded_credits_not_user_editable(self):
        self.assertFalse((ROOT/'credits.ini').exists())
        self.assertFalse((ROOT/'credits_loader.py').exists())
        app=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertNotIn('_open_credits_ini',app)
        self.assertNotIn('QLineEdit',app[app.index('def _make_about(self)'):app.index('def _open_log(self)')])
        self.assertIsInstance(get_special_thanks(), tuple)

    def test_first_run_and_live_combo_exists(self):
        app=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('class LanguagePicker(QDialog)',app)
        self.assertIn('self.language_combo.currentIndexChanged.connect(self._request_language)',app)
        self.assertIn('self.window.language_requested.connect(self.change_language)',app)
        self.assertIn("self.store.setValue('general/ui_language', code)",app)
        self.assertIn('self.overlay.retranslate()',app)
        self.assertIn('self.tray_actions',app)

    def test_preserved_original_modern_black(self):
        app=(ROOT/'app.py').read_text(encoding='utf-8')
        for text in ('self.resize(1020, 690)', 'sidebar.setFixedWidth(226)',
                     'QFrame#panel { background:#17191E;',
                     'class Overlay(QDialog)', 'class SlotEditor(QWidget)'):
            self.assertIn(text,app)

if __name__ == '__main__': unittest.main()
