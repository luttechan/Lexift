import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
import app
from hotkeys_windows import HotkeyBinding
from layout_profiles import create_layout, hkl_string


class StartupPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = QSettings(str(Path(self.temp.name) / 'settings.ini'), QSettings.Format.IniFormat)
        self.store.setValue('hotkey/mode', 'ctrl_shift')
        self.store.setValue('hotkey/key', 'E')
        self.slots = [dict(hkl=hkl_string(0x0412), mode='ko_hangul', name='Korean')]
        self.layouts = patch.object(app, 'available_layouts', return_value=[create_layout(0x0412)])
        self.layouts.start()
        self.window = app.MainWindow(self.store, self.slots, False)

    def tearDown(self):
        self.window.hide()
        self.window.deleteLater()
        self.qt.processEvents()
        self.layouts.stop()
        self.temp.cleanup()

    def test_all_settings_exist_before_the_first_menu_click(self):
        self.assertEqual(self.window._ready_pages, {0, 1, 2, 3, 4})
        with patch.object(self.window, '_make_preferences', side_effect=AssertionError('menu rebuilt')), \
             patch.object(self.window, '_make_about', side_effect=AssertionError('menu rebuilt')), \
             patch.object(self.window, '_make_dictionary', side_effect=AssertionError('menu rebuilt')):
            for index in (2, 3, 4, 2, 1, 3, 0, 4):
                self.window.navigate(index)
                self.assertEqual(self.window.pages.currentIndex(), index)
        self.assertEqual(self.window.pages.count(), 5)

    def test_settings_created_on_first_visit_with_saved_shortcut(self):
        self.window.navigate(2)
        self.assertEqual(self.window.shortcut_modifier.currentData(), 'ctrl_shift')
        self.assertEqual(self.window.shortcut_key.currentData(), 'E')
        page = self.window.pages.widget(2)
        self.window.navigate(0)
        self.window.navigate(2)
        self.assertIs(self.window.pages.widget(2), page)

    def test_shortcut_update_before_and_after_settings_creation(self):
        binding = HotkeyBinding('ctrl_alt', 'F9')
        self.store.setValue('hotkey/mode', binding.mode)
        self.store.setValue('hotkey/key', binding.key)
        self.window.update_shortcut_ui(binding)
        self.assertEqual(self.window.dashboard_shortcut.text(), binding.title)
        self.window.navigate(2)
        self.assertEqual(self.window.shortcut_key.currentData(), 'F9')

    def test_about_created_in_place_in_either_visit_order(self):
        self.window.navigate(3)
        self.assertTrue(hasattr(self.window, 'special_list'))
        about = self.window.pages.widget(3)
        self.window.navigate(2)
        self.window.navigate(3)
        self.assertIs(self.window.pages.widget(3), about)
        self.assertEqual(self.window.pages.currentIndex(), 3)

    def test_font_selection_never_enumerates_installed_families(self):
        with patch.object(QFontDatabase, 'families', side_effect=AssertionError('font scan')):
            app.choose_font(self.qt)
        self.assertEqual(self.qt.font().family(), 'Malgun Gothic')

    def test_language_dropdown_avoids_measuring_all_scripts(self):
        from PySide6.QtWidgets import QComboBox
        from PySide6.QtCore import Qt
        self.window.navigate(2)
        combo = self.window.language_combo
        self.assertEqual(combo.sizeAdjustPolicy(),
                         QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.assertEqual(combo.count(), len(app.LANGUAGES))
        expected = {'ja': 'Yu Gothic UI', 'zh_CN': 'Microsoft YaHei UI',
                    'zh_TW': 'Microsoft JhengHei UI'}
        for code, family in expected.items():
            font = combo.itemData(combo.findData(code), Qt.ItemDataRole.FontRole)
            self.assertEqual(font.family(), family)

    def test_japanese_credit_uses_matching_font_without_changing_text(self):
        from PySide6.QtWidgets import QLabel
        with patch.object(app, 'get_special_thanks', return_value=(('Japanese', '澤井亮介'),)):
            self.window._reload_special_thanks()
            self.window.navigate(3)
        names = [w for w in self.window.special_host.findChildren(QLabel)
                 if w.text() == '澤井亮介']
        self.assertEqual(len(names), 1)
        self.assertIn('Yu Gothic UI', names[0].styleSheet())

    def test_about_revisit_reuses_existing_credit_widgets(self):
        self.window.navigate(3)
        with patch.object(self.window, '_reload_special_thanks') as reload:
            self.window.navigate(0)
            self.window.navigate(3)
        reload.assert_not_called()
