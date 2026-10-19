import unittest
from dataclasses import replace
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox
import app
from i18n import set_language, text_font_family
from layout_profiles import create_layout


class ScriptFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def tearDown(self):
        set_language('ko')

    def test_os_language_names_keep_korean_font_in_japanese_ui(self):
        set_language('ja')
        layout = replace(create_layout(0x0419),name='러시아어(러시아)',is_ime=True)
        slots = [dict(hkl=layout.hkl,mode='ime_native',name='custom')]
        with patch.object(app,'available_layouts',return_value=[layout]):
            editor = app.SlotEditor(slots)
        try:
            modes = next(combo for combo in editor.findChildren(QComboBox) if combo.findData('ime_native')>=0)
            native_index = modes.findData('ime_native')
            self.assertEqual(modes.itemData(native_index,Qt.ItemDataRole.FontRole).family(),'Malgun Gothic')
            self.assertEqual(modes.property('kanashiftTextFamily'),'Malgun Gothic')
            modes.setCurrentIndex(modes.findData('ime_latin'))
            self.assertEqual(modes.property('kanashiftTextFamily'),'Yu Gothic UI')
            self.assertEqual(editor.slots[0]['mode'],'ime_latin')
        finally:
            editor.deleteLater()
            self.qt.processEvents()

    def test_script_family_preserves_korean_default_and_native_cjk_text(self):
        for code, family in (('ja','Yu Gothic UI'),('zh_CN','Microsoft YaHei UI'),('zh_TW','Microsoft JhengHei UI')):
            set_language(code)
            self.assertEqual(text_font_family('한국어 / English'),'Malgun Gothic')
            self.assertEqual(text_font_family('日本語'),'Yu Gothic UI' if code=='ja' else family)
            self.assertEqual(text_font_family('ひらがな'),'Yu Gothic UI')

    def test_typing_same_script_does_not_reapply_styles_on_every_character(self):
        widget = app.label('English')
        try:
            with patch.object(widget,'setStyleSheet') as restyle:
                for text in ('E','En','Eng','English'):
                    app.apply_text_font(widget,text)
            restyle.assert_not_called()
            app.apply_text_font(widget,'日本語')
            self.assertEqual(widget.property('kanashiftTextFamily'),'Yu Gothic UI')
            app.apply_text_font(widget,'한국어')
            self.assertEqual(widget.property('kanashiftTextFamily'),'Malgun Gothic')
        finally:
            widget.deleteLater()
