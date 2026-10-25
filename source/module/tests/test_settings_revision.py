"""Settings interactions through owned Qt widgets, with isolated preferences."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QSettings, Qt, QPoint, QPointF, QCoreApplication, QEvent
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
import app
from dictionary_ui import DictionaryEditor
from i18n import LANGUAGES, set_language, tr


class SettingsRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)
    def setUp(self):
        set_language('ko')
        self.folder=tempfile.TemporaryDirectory()
        self.store=QSettings(str(Path(self.folder.name)/'prefs.ini'),QSettings.Format.IniFormat)
        self.window=app.MainWindow(self.store,[],False)
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.window._preferences_timer.stop()
    def tearDown(self):
        self.window.hide();self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.qt.processEvents();self.folder.cleanup();set_language('ko')
    def test_closed_focused_dropdowns_do_not_change_with_wheel(self):
        w=self.window;w.navigate(2);w.show();self.qt.processEvents()
        for combo in (w.shortcut_modifier,w.shortcut_key,w.ime_modifier,w.ime_key,
                      w.chinese_modifier,w.chinese_key,w.traditional_modifier,w.traditional_key,w.language_combo):
            combo.setFocus();before=combo.currentIndex()
            event=QWheelEvent(QPointF(5,5),QPointF(combo.mapToGlobal(QPoint(5,5))),
                QPoint(),QPoint(0,-120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,
                Qt.ScrollPhase.NoScrollPhase,False)
            QApplication.sendEvent(combo,event)
            self.assertEqual(combo.currentIndex(),before)
        w.shortcut_key.setCurrentIndex(w.shortcut_key.findData('B'))
        self.assertEqual(w.shortcut_key.currentData(),'B')
    def test_language_change_requires_confirmation_and_cancel_restores_field(self):
        w=self.window;events=[];w.language_requested.connect(events.append)
        with patch.object(app.QMessageBox,'question',return_value=app.QMessageBox.StandardButton.No) as dialog:
            w.language_combo.setCurrentIndex(w.language_combo.findData('ja'))
        self.assertEqual(events,[]);self.assertEqual(w.language_combo.currentData(),'ko')
        self.assertIn('日本語',dialog.call_args.args[2])
        with patch.object(app.QMessageBox,'question',return_value=app.QMessageBox.StandardButton.Yes):
            w.language_combo.setCurrentIndex(w.language_combo.findData('en'))
        self.assertEqual(events,['en'])
    def test_confirmation_texts_are_translated_in_every_ui_language(self):
        for code,_ in LANGUAGES:
            set_language(code)
            for key in ('기본값','정말로 {language}로 변경하시겠습니까?',
                        '모든 설정을 기본값으로 되돌릴까요? 단축키, 표시 언어, 실행 옵션, 입력기 슬롯과 사용자 사전이 초기화됩니다.'):
                self.assertNotEqual(tr(key),key) if code!='ko' else self.assertEqual(tr(key),key)
            self.assertIn('English',tr('정말로 {language}로 변경하시겠습니까?').format(language='English'))
    def test_defaults_cancel_is_a_no_op_and_accept_emits_once(self):
        events=[];self.window.defaults_requested.connect(lambda:events.append(True))
        for answer in (app.QMessageBox.StandardButton.No,app.QMessageBox.StandardButton.Yes):
            with patch.object(app.QMessageBox,'question',return_value=answer):
                self.window.defaults_button.click()
            self.assertEqual(events,[] if answer==app.QMessageBox.StandardButton.No else [True])
    def test_row_buttons_remove_clicked_row_after_previous_removal_and_save(self):
        entries=[dict(keyword=k,text=t,language='ja') for k,t in [('하나','一'),('둘','二'),('셋','三')]]
        editor=DictionaryEditor(entries);editor.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        editor.resize(700,280);editor.show();self.qt.processEvents()
        try:
            for row,remaining in ((1,['하나','셋']),(0,['셋'])):
                index=editor.model.index(row,3)
                QTest.mouseClick(editor.table.viewport(),Qt.MouseButton.LeftButton,
                                 pos=editor.table.visualRect(index).center())
                self.assertEqual([e['keyword'] for e in editor.model.rows],remaining)
            saved=[];editor.saved.connect(saved.append);editor.save()
            self.assertEqual(saved,[[entries[2]]])
            self.assertFalse(editor.model.setData(editor.model.index(0,3),'oops'))
        finally:editor.hide();editor.deleteLater()
    def test_large_dictionary_does_not_allocate_per_row_buttons(self):
        editor=DictionaryEditor([dict(keyword='스미네',text='澄音',language='ja') for _ in range(1000)])
        try:
            self.assertEqual(editor.model.rowCount(),1000)
            self.assertLess(len(editor.findChildren(QPushButton)),10)
            delegate=editor.table.itemDelegate()
            combo=delegate.createEditor(editor.table,None,editor.model.index(0,2))
            combo.setCurrentIndex(0)
            event=QWheelEvent(QPointF(5,5),QPointF(5,5),QPoint(),QPoint(0,-120),
                Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
            QApplication.sendEvent(combo,event);self.assertEqual(combo.currentIndex(),0)
        finally:editor.deleteLater()
