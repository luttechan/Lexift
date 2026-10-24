import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QComboBox
import app
from layout_profiles import create_layout


class MenuResponsivenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def test_mode_change_keeps_rows_focus_and_custom_names(self):
        layout = create_layout(0x0411)
        slots = [dict(hkl=layout.hkl, mode='ja_hiragana', name='My Japanese')]
        with patch.object(app, 'available_layouts', return_value=[layout]):
            editor = app.SlotEditor(slots)
        row = editor.list_layout.itemAt(0).widget()
        name = editor._name_editors[0]
        with patch.object(editor, 'rebuild') as rebuild:
            editor._select_mode(0, 'ja_katakana_full')
            self.qt.processEvents()
        rebuild.assert_not_called()
        self.assertIs(editor.list_layout.itemAt(0).widget(), row)
        self.assertEqual(name.text(), 'My Japanese')
        self.assertEqual(editor.slots[0]['mode'], 'ja_katakana_full')
        editor.slots[0]['name'] = app.default_name(layout, 'ja_katakana_full')
        editor._select_mode(0, 'ja_hiragana')
        self.assertEqual(name.text(), app.default_name(layout, 'ja_hiragana'))
        editor.deleteLater()

    def test_same_page_selection_does_not_restyle_buttons(self):
        with tempfile.TemporaryDirectory() as directory:
            store = QSettings(str(Path(directory)/'prefs.ini'), QSettings.Format.IniFormat)
            with patch.object(app, 'available_layouts', return_value=[]):
                window = app.MainWindow(store, [], False)
            with patch.object(window.pages, 'setCurrentIndex') as change:
                window.navigate(0)
            change.assert_not_called()
            window.deleteLater()
            self.qt.processEvents()

    def test_popup_animations_disabled(self):
        app.choose_font(self.qt)
        for effect in (Qt.UIEffect.UI_AnimateCombo, Qt.UIEffect.UI_AnimateMenu,
                       Qt.UIEffect.UI_FadeMenu):
            self.assertFalse(self.qt.isEffectEnabled(effect))
