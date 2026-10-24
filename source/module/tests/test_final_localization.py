"""Guard catalog coverage, translated dialog buttons, live updates and UI lifetimes."""
import ast
import re
import tempfile
import unittest
from pathlib import Path
from string import Formatter
from unittest.mock import Mock, patch
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
import app
import i18n
from localized_dialogs import QMessageBox
from layout_profiles import create_layout, default_name
from update_ui import UpdateResult, UpdateProgress
from update_core import UpdateError
import native_language_dialog as native

ROOT=Path(__file__).resolve().parents[1]

class FinalLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        i18n.set_language('ko')
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_every_literal_translation_key_is_in_all_catalogs(self):
        for path in [*ROOT.glob('*.py'),ROOT.parent/'launch.pyw']:
            if path.name=='i18n.py':continue
            tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                        and node.func.id in ('tr','tr_mode') and node.args
                        and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)):
                    for code,catalog in i18n.CATALOG.items():
                        self.assertIn(node.args[0].value,catalog,(path.name,node.lineno,code))

    def test_placeholder_parity_and_no_korean_fallback_in_other_languages(self):
        fields=lambda text:{name for _,name,_,_ in Formatter().parse(text) if name is not None}
        for code,catalog in i18n.CATALOG.items():
            for key,value in catalog.items():
                self.assertTrue(value.strip(),(code,key))
                self.assertEqual(fields(key),fields(value),(code,key))
                self.assertIsNone(re.search('[가-힣]',value),(code,key))

    def test_stock_buttons_follow_selected_language_instead_of_windows(self):
        dialog=QMessageBox()
        try:
            for code,_ in i18n.LANGUAGES:
                i18n.set_language(code)
                dialog.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No|
                                          QMessageBox.StandardButton.Ok|QMessageBox.StandardButton.Cancel)
                for value,key in ((QMessageBox.StandardButton.Yes,'예'),(QMessageBox.StandardButton.No,'아니요'),
                                  (QMessageBox.StandardButton.Ok,'확인'),(QMessageBox.StandardButton.Cancel,'취소')):
                    self.assertEqual(dialog.button(value).text(),i18n.tr(key))
        finally:dialog.deleteLater()

    def test_update_dialogs_retranslate_without_restarting_request(self):
        i18n.set_language('ko')
        result=UpdateResult('0.7.7','0.7.8',i18n.tr('업데이트가 필요합니다.'),i18n.tr('다운로드 및 설치'),Mock())
        progress=UpdateProgress(i18n.tr('다운로드 및 파일 확인 중...'),True)
        try:
            for code,_ in i18n.LANGUAGES:
                i18n.set_language(code);result.retranslate();progress.retranslate()
                self.assertEqual(result.status.text(),i18n.tr('업데이트가 필요합니다.'))
                self.assertEqual(result.install_button.text(),i18n.tr('다운로드 및 설치'))
                self.assertEqual(result.close_button.text(),i18n.tr('닫기'))
                self.assertIn(i18n.tr('현재 버전'),result.versions.text())
                self.assertEqual(progress.label.text(),i18n.tr('다운로드 및 파일 확인 중...'))
                self.assertEqual(progress.cancel_button.text(),i18n.tr('취소'))
        finally:result.deleteLater();progress.deleteLater()

    def test_raw_errors_are_logged_separately_from_localized_instructions(self):
        for code,_ in i18n.LANGUAGES:
            i18n.set_language(code)
            for error,context in ((UpdateError('HTTP 403 Forbidden'),'update'),
                                  (UpdateError('ZIP manifest hash mismatch'),'update'),
                                  (RuntimeError('키보드 후크 등록 실패 (Win32 5)'),'shortcut'),
                                  (PermissionError('Access denied'),'update')):
                text=i18n.error_text(error,context)
                self.assertNotEqual(text,str(error))
                if code!='ko':self.assertIsNone(re.search('[가-힣]',text))

    def test_os_input_names_are_localized_and_custom_slot_names_are_untouched(self):
        layout=create_layout(0x0419,name='러시아어(러시아)')
        for code,_ in i18n.LANGUAGES:
            i18n.set_language(code)
            self.assertIn(i18n.tr('러시아어'),layout.display)
        japanese=create_layout(0x0411)
        self.assertEqual(default_name(japanese,'ja_katakana_half'),'ｶﾀｶﾅ · 半角')

    def test_removed_nested_layouts_do_not_accumulate(self):
        host=QWidget();root=QVBoxLayout(host)
        try:
            for _ in range(100):
                row=QHBoxLayout();root.addLayout(row)
                row.addWidget(app.label('temporary'))
                app.clear_layout(root)
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
            self.assertEqual(len(host.findChildren(QHBoxLayout)),0)
            self.assertEqual(root.count(),0)
        finally:host.deleteLater()

    def test_native_exit_captions_are_translated_and_cancel_is_default(self):
        def invoke(config,chosen,_radio,_verify):
            data=config._obj
            self.assertEqual(data.nDefaultButton,7)
            self.assertEqual(data.pszMainInstruction,i18n.tr('정말로 종료하시겠습니까?'))
            self.assertEqual(data.pButtons[0].pszButtonText,i18n.tr('종료'))
            self.assertEqual(data.pButtons[1].pszButtonText,i18n.tr('취소'))
            chosen._obj.value=7
            return 0
        api=Mock();api.TaskDialogIndirect.side_effect=invoke
        with patch.object(native.ctypes,'WinDLL',return_value=api):
            for code,_ in i18n.LANGUAGES:
                i18n.set_language(code)
                self.assertFalse(native.confirm_quit())

    def test_slot_counts_use_correct_singular_and_plural(self):
        for code,word in (('en','input'),('fr','saisie'),('es','entrada'),('de','Eingabe')):
            i18n.set_language(code)
            self.assertEqual(i18n.tr_count(1,'Q'),f'1 {word} · Q')
        i18n.set_language('ru')
        for count,word in ((1,'раскладка'),(2,'раскладки'),(5,'раскладок'),(11,'раскладок'),(21,'раскладка')):
            self.assertEqual(i18n.tr_count(count,'Q'),f'{count} {word} · Q')
