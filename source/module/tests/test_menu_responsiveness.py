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

    def test_selector_prepares_without_painting_and_reuses_its_tiles(self):
        layout=create_layout(0x0412)
        overlay=app.Overlay()
        slots=[dict(hkl=layout.hkl,mode='ko_hangul',name='Korean')]
        with patch.object(app,'available_layouts',return_value=[layout]),patch.object(overlay,'show') as show,patch.object(overlay,'grab') as grab:
            overlay.prepare_slots(slots)
            first=list(overlay.tiles);overlay.rebuild(slots)
            self.assertEqual(overlay.tiles,first)
            show.assert_not_called();grab.assert_not_called()
        overlay.deleteLater();self.qt.processEvents()

    def test_slot_move_delete_preserve_controls_and_edit_the_correct_row(self):
        from PySide6.QtCore import QEvent,QCoreApplication
        layout=create_layout(0x0412)
        slots=[dict(hkl=layout.hkl,mode='ko_hangul',name=name) for name in ('one','two','three')]
        with patch.object(app,'available_layouts',return_value=[layout]):editor=app.SlotEditor(slots)
        original=list(editor._slot_rows);names=list(editor._name_editors)
        with patch.object(editor,'rebuild',side_effect=AssertionError('rebuilt unrelated rows')):
            editor.move_slot(0,1)
            self.assertEqual(editor._slot_rows,[original[1],original[0],original[2]])
            names[0].textEdited.emit('moved')
            self.assertEqual([s['name'] for s in editor.slots],['two','moved','three'])
            modes=original[0].findChildren(QComboBox)[1]
            modes.setCurrentIndex(modes.findData('ko_latin'))
            self.assertEqual(editor.slots[1]['mode'],'ko_latin')
            self.assertEqual(editor.slots[0]['mode'],'ko_hangul')
            original[1].remove_button.click()
            self.assertEqual(editor._slot_rows,[original[0],original[2]])
            names[2].textEdited.emit('last')
            self.assertEqual([s['name'] for s in editor.slots],['moved','last'])
            self.assertFalse(original[0].up_button.isEnabled())
            self.assertFalse(original[2].down_button.isEnabled())
            original[0].remove_button.click()
            self.assertFalse(original[2].remove_button.isEnabled())
        editor.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_large_dictionary_header_does_not_scan_all_rows(self):
        from dictionary_ui import DictionaryEditor
        editor=DictionaryEditor([dict(keyword='스미네',text='澄音',language='ja') for _ in range(1000)])
        editor.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen);editor.resize(700,300)
        with patch.object(editor.model,'headerData',wraps=editor.model.headerData) as header:
            editor.show();editor.grab()
            self.assertLess(header.call_count,200)
        editor.hide();editor.deleteLater();self.qt.processEvents()

    def test_dictionary_at_capacity_does_not_start_editing_the_last_row(self):
        from dictionary_ui import DictionaryEditor
        editor=DictionaryEditor([dict(keyword='스미네',text='澄音',language='ja') for _ in range(1000)])
        self.assertFalse(editor.add_button.isEnabled())
        with patch.object(editor.table,'edit') as edit:
            editor.add();edit.assert_not_called()
        editor.model.remove(4)
        self.assertTrue(editor.add_button.isEnabled())
        with patch.object(editor.table,'edit') as edit:
            editor.add();edit.assert_called_once()
        self.assertEqual(editor.model.rowCount(),1000)
        self.assertFalse(editor.add_button.isEnabled())
        editor.deleteLater();self.qt.processEvents()
