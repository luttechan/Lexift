from contextlib import ExitStack
import gc
import json
from pathlib import Path
import tempfile
import threading
import time
import unicodedata
import unittest
from unittest.mock import Mock,patch
from PySide6.QtCore import QSettings,QCoreApplication,QEvent,Qt
from PySide6.QtWidgets import QApplication,QLabel,QWidget
import app
from custom_dictionary import CustomDictionary,KEY,validate
from dictionary_ui import DictionaryEditor
from hotkeys_windows import HotkeyBinding
from i18n import set_language,tr,LANGUAGES
from layout_profiles import create_layout
from notification_sound import NotificationSound,sound_path
REAL_WARM=app.LexiftController._warm_keyboard


class ConversionSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([]);cls.qt.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.stack=ExitStack();self.folder=tempfile.TemporaryDirectory()
        self.store=QSettings(str(Path(self.folder.name)/'prefs.ini'),QSettings.Format.IniFormat)
        layout=create_layout(0x412)
        self.store.setValue('profiles/slots_json',json.dumps([dict(hkl=layout.hkl,mode='ko_hangul',name='Korean')]))
        self.stack.enter_context(patch.object(app,'QSettings',return_value=self.store))
        self.stack.enter_context(patch.object(app,'available_layouts',return_value=[layout]))
        self.stack.enter_context(patch.object(app,'CapsQHook',side_effect=lambda *a,**k:Mock(on_hotkey=a[0],on_ime=k.get('on_ime'),on_chinese=k.get('on_chinese'))))
        self.stack.enter_context(patch.object(app,'OverlayNavigationHook'))
        self.stack.enter_context(patch.object(app.LexiftController,'_warm_keyboard',return_value=False))
        self.stack.enter_context(patch.object(app,'keyboard_service'))
        self.sound=self.stack.enter_context(patch.object(app.LexiftController,'_sound'))
        self.mode=Mock(enabled=False,language='ja',engines={})
        self.stack.enter_context(patch('ime_inline.inline_mode',return_value=self.mode))
        self.c=app.LexiftController(self.qt);self.c._engine_prepare_timer.stop()
        self.c._start_hook(notify=False)
    def tearDown(self):
        c=self.c
        c._engine_prepare_timer.stop();c.tray.hide();c.tray.hide_notification();c.tray.deleteLater()
        if c._window:c._window.hide();c._window.deleteLater()
        c.overlay.deleteLater();c.cursor_indicator.deleteLater();c.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.qt.processEvents()
        self.stack.close();self.folder.cleanup();set_language('ko')
    def test_independent_flags_persist_and_remove_disabled_shortcuts(self):
        c=self.c;c.set_feature_enabled('selector',False)
        self.assertIsNone(c.hook.on_hotkey);self.assertIsNotNone(c.hook.on_ime);self.assertTrue(c.features['zh'])
        c.set_feature_enabled('ja',False);self.mode.release.assert_called_with('ja')
        self.assertIsNone(c.hook.on_ime);self.assertIsNotNone(c.hook.on_chinese)
        c.set_feature_enabled('zh',False)
        self.assertFalse(c._running);self.assertFalse(any(c.features.values()))
        for name in c.features:self.assertFalse(self.store.value('features/'+name,type=bool))
        c.set_feature_enabled('zh',True)
        self.assertTrue(c._running);self.assertIsNone(c.hook.on_hotkey);self.assertIsNotNone(c.hook.on_chinese)
        self.assertFalse(c.features['selector']);self.assertFalse(c.features['ja'])
    def test_keyboard_startup_is_asynchronous_and_cancelled_when_disabled(self):
        entered=threading.Event();release=threading.Event();worker=app.keyboard_service()
        worker.connection=None
        worker.ensure_started.side_effect=lambda:(entered.set(),release.wait(2))
        started=time.perf_counter()
        try:
            self.assertTrue(REAL_WARM(self.c,False))
            self.assertLess(time.perf_counter()-started,.1)
            self.assertTrue(entered.wait(1));self.c._enabled=False
        finally:release.set();self.c._hook_warm_thread.join(2)
        self.qt.processEvents()
        worker.close.assert_called_with(wait=False)
    def test_feature_checkbox_next_to_shortcuts_and_survives_ui_language(self):
        c=self.c;c.window.navigate(2)
        self.assertEqual(set(c.window.feature_checks),{'selector','ja','zh'})
        c.window.feature_checks['ja'].setChecked(False)
        self.assertFalse(c.features['ja'])
        c.change_language('en')
        self.assertFalse(c.window.feature_checks['ja'].isChecked())
        self.assertTrue(c.window.feature_checks['zh'].isChecked())
        self.assertTrue(any('may not be supported' in label.text() for label in c.window.findChildren(QLabel)))
    def test_failure_restores_feature_flags_and_checkbox(self):
        c=self.c;c.window.navigate(2);old=c.hook
        failed=Mock();failed.start.side_effect=RuntimeError('occupied')
        restored=Mock()
        with patch.object(c,'_make_keyboard_hook',side_effect=[failed,restored]),patch.object(app.QMessageBox,'warning'):
            c.set_feature_enabled('ja',False)
        self.assertTrue(c.features['ja']);self.assertTrue(c.window.feature_checks['ja'].isChecked())
        restored.start.assert_called_once();self.assertTrue(c._running)
        self.mode.release.assert_not_called()
    def test_non_hangul_modes_do_not_toggle_or_change_the_ime(self):
        c=self.c
        with patch.object(app,'target_is_foreground',return_value=True),patch.object(app,'current_language') as lang,patch.object(app,'korean_is_hangul') as hangul,patch.object(app,'request_hkl') as request:
            for conversion in ('ja','zh'):
                for code,status in ((0x409,False),(0x411,True),(0x412,False),(0x412,None)):
                    lang.return_value=code;hangul.return_value=status
                    c._show_ime_panel(123,conversion)
            self.mode.toggle.assert_not_called();request.assert_not_called()
            c._korean_activation.activate.assert_not_called() if isinstance(c._korean_activation.activate,Mock) else None
        self.sound.assert_not_called()
    def test_hangul_allows_toggle_but_off_is_always_available(self):
        c=self.c;c._ime_toast=Mock();c._ime_toast.width.return_value=120;c._ime_toast_timer=Mock()
        self.mode.toggle.return_value=True
        with patch.object(app,'target_is_foreground',return_value=True),patch.object(app,'current_language',return_value=0x412),patch.object(app,'korean_is_hangul',return_value=True) as check:
            c._show_ime_panel(123,'zh')
            check.assert_called_once_with(123,timeout_ms=15)
        self.mode.toggle.assert_called_once_with('zh');self.sound.assert_called_once()
        self.mode.enabled=True;self.mode.language='zh';self.mode.toggle.reset_mock();c._last_ime_toggle=0
        with patch.object(app,'current_language',return_value=0x409),patch.object(app,'korean_is_hangul') as check:
            c._show_ime_panel(123,'zh')
            check.assert_not_called()
        self.mode.toggle.assert_called_once_with('zh')
    def test_disabled_selector_and_conversion_ignore_queued_events(self):
        c=self.c;c.set_feature_enabled('selector',False);c.set_feature_enabled('ja',False)
        with patch.object(c.overlay,'open') as opened,patch.object(app,'request_hkl') as request:
            c._hotkey(123);c.show_overlay();c.apply_slot(c.slots[0]);c._show_ime_panel(123,'ja')
        opened.assert_not_called();request.assert_not_called();self.mode.toggle.assert_not_called()
    def test_dictionary_saves_and_unsaved_edits_survive_language_change(self):
        c=self.c;c.window.navigate(4)
        rows=[dict(keyword='스미네',text='澄音',language='ja')]
        c.window.dictionary_editor.model.rows=[dict(e) for e in rows]
        c.save_dictionary(rows)
        self.assertEqual(CustomDictionary(self.store).lookup('ja','스미네'),'澄音')
        c.window.dictionary_editor.model.rows[0]['text']='澄音さん'
        c.change_language('ja')
        self.assertEqual(c.window.dictionary_editor.model.rows[0]['text'],'澄音さん')
        self.assertEqual(c.custom_dictionary.lookup('ja','스미네'),'澄音')


class DictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_language_scoping_normalization_and_priority_without_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            store=QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat);dictionary=CustomDictionary(store)
            dictionary.replace([dict(keyword='스미네',text='澄音',language='ja'),dict(keyword='스미네',text='名字',language='zh')])
            self.assertEqual(dictionary.lookup('ja',unicodedata.normalize('NFD','스미네')),'澄音')
            self.assertEqual(dictionary.lookup('zh','스미네'),'名字')
            self.assertIsNone(dictionary.lookup('ja','스미네상'))
            data={'candidates':['私','澄音','住みね'],'readings':['わたし','すみね','すみね'],'kana':'すみね'}
            answer=dictionary.merge('ja','스미네',data)
            self.assertEqual(answer['candidates'],['澄音','私','住みね'])
            self.assertEqual(len(answer['readings']),len(answer['candidates']))
            self.assertEqual(data['candidates'][0],'私')
    def test_invalid_entries_leave_saved_dictionary_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            store=QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat);dictionary=CustomDictionary(store)
            row=dict(keyword='스미네',text='澄音',language='ja');dictionary.replace([row]);saved=store.value(KEY)
            for entries in ([row,row],[dict(row,keyword='abc')],[dict(row,text='')],[dict(row,language='en')],[row]*1001):
                with self.assertRaises(ValueError):dictionary.replace(entries)
                self.assertEqual(store.value(KEY),saved)
            store.setValue(KEY,'invalid json');CustomDictionary(store)
            self.assertEqual(store.value(KEY),'invalid json')
    def test_virtual_editor_supports_1000_rows_without_cell_widgets(self):
        rows=[dict(keyword='단어'+chr(0xac00+n),text='澄音',language='ja') for n in range(1000)]
        editor=DictionaryEditor(rows)
        self.assertEqual(editor.model.rowCount(),1000)
        self.assertLess(len(editor.findChildren(QWidget)),40)
        self.assertIsNone(editor.table.indexWidget(editor.model.index(999,2)))
        editor.deleteLater()
    def test_custom_candidate_is_present_even_with_empty_engine_response(self):
        from ime_inline import InlineMode
        with tempfile.TemporaryDirectory() as folder:
            dictionary=CustomDictionary(QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat))
            dictionary.replace([dict(keyword='스미네',text='澄音',language='ja')])
            mode=InlineMode();mode.dictionary=dictionary;mode.enabled=True;mode.query=Mock()
            mode.snapshot={'source':'스미네'}
            with patch.object(mode,'_show') as show:
                mode._queried(mode.query,{'source':'스미네','kana':'すみね','candidates':[]})
                show.assert_called_once()
            self.assertEqual(dictionary.merge('ja','스미네',show.call_args.args[0])['candidates'][0],'澄音')
            mode.query=None;mode.close();mode.deleteLater()


class NotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_supplied_wave_is_packaged(self):
        import hashlib
        self.assertEqual(hashlib.sha256(sound_path().read_bytes()).hexdigest(),'e134873ca4fd9140e5a90ed5d57814115b2f283dacde68de138b25a5c80ec264')
    def test_audio_worker_is_nonblocking_and_bounded_under_notification_bursts(self):
        entered=threading.Event();release=threading.Event();calls=[]
        def player(path):calls.append(path);entered.set();release.wait(2)
        sound=NotificationSound(player)
        try:
            sound.play();self.assertTrue(entered.wait(1))
            started=time.perf_counter()
            for _ in range(1000):sound.play()
            self.assertLess(time.perf_counter()-started,.1);self.assertTrue(sound.pending)
            self.assertEqual(len(calls),1)
        finally:
            sound.close();release.set();sound.thread.join(2)
        self.assertFalse(sound.thread.is_alive());self.assertEqual(calls,[sound_path()])
    def test_general_notifications_reuse_one_toast_and_play_the_same_sound(self):
        from notifications import NotificationTray
        tray=NotificationTray(app.icon())
        try:
            with patch('notifications.notify_event') as sound,patch('notifications.NotificationToast.present'):
                for text in ('startup','saved','warning','background'):
                    tray.showMessage('Lexift',text)
                self.assertEqual(sound.call_count,4)
                toast=tray.toast
                tray.showMessage('Lexift','again')
                self.assertIs(toast,tray.toast)
        finally:tray.hide_notification();tray.deleteLater()

    def test_closed_message_boxes_are_released(self):
        from localized_dialogs import QMessageBox
        parent=QWidget()
        with patch.object(QMessageBox,'exec',return_value=0),patch('notification_sound.notify_event') as sound:
            for _ in range(20):QMessageBox.information(parent,'Lexift','test')
            self.assertEqual(sound.call_count,20)
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.assertEqual(parent.findChildren(QMessageBox),[]);parent.deleteLater()

    def test_disabled_selector_is_omitted_from_worker_registration(self):
        import isolated_hotkeys as hooks
        worker=Mock()
        with patch.object(hooks,'service',return_value=worker):
            proxy=hooks.CapsQHook(None,on_ime=Mock());proxy.start()
        self.assertFalse(worker.command.call_args.kwargs['selector'])
        self.assertTrue(worker.command.call_args.kwargs['ime'])

    def test_stale_selector_event_does_not_disconnect_the_worker(self):
        import isolated_hotkeys as hooks
        import socket
        first,second=socket.socketpair();worker=hooks.HookService();callback=Mock()
        worker.connection=second;worker.caps=hooks.CapsQHook(None,on_ime=callback)
        try:
            first.sendall(b'{"event":"hotkey","hwnd":123}\n{"event":"ime","hwnd":123}\n')
            first.shutdown(socket.SHUT_WR);worker._read(second)
            callback.assert_called_once_with(123)
        finally:worker.connection=None;first.close();second.close()

    def test_finished_search_threads_release_their_keep_alive_before_client_deletion(self):
        import chinese_query_client as chinese
        with patch.object(chinese.SearchThread,'run',lambda self:None):
            for _ in range(40):
                client=chinese.ChineseQueryClient();client.start()
                deadline=time.monotonic()+2
                while chinese._running_threads and time.monotonic()<deadline:
                    self.qt.processEvents();time.sleep(.001)
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
                self.assertFalse(chinese._running_threads)
