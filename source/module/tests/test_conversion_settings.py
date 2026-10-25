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


class BrandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_dark_wordmark_has_contrast_and_preserves_transparency_and_original(self):
        from PySide6.QtGui import QImage
        import hashlib
        source=Path(app.__file__).parent/'Style/Lexift_black.png'
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        for dark in (True,False):
            widget=app.brand_mark(dark=dark)
            image=widget.findChild(QLabel).pixmap().toImage()
            self.assertEqual(image.pixelColor(0,0).alpha(),0)
            visible=[image.pixelColor(x,y).lightness() for y in range(image.height())
                     for x in range(image.width()) if image.pixelColor(x,y).alpha()>192]
            self.assertTrue(visible)
            average=sum(visible)/len(visible)
            self.assertGreater(average,200) if dark else self.assertLess(average,55)
            widget.deleteLater()
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)


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
        self.stack.enter_context(patch.object(app,'CapsQHook',side_effect=lambda *a,**k:Mock(on_hotkey=a[0],on_ime=k.get('on_ime'),on_chinese=k.get('on_chinese'),on_traditional=k.get('on_traditional'))))
        self.stack.enter_context(patch.object(app,'OverlayNavigationHook'))
        self.stack.enter_context(patch.object(app.LexiftController,'_warm_keyboard',return_value=False))
        self.stack.enter_context(patch.object(app,'keyboard_service'))
        self.sound=self.stack.enter_context(patch.object(app.LexiftController,'_sound'))
        self.mode=Mock(enabled=False,language='ja',engines={})
        self.stack.enter_context(patch('ime_inline.inline_mode',return_value=self.mode))
        self.c=app.LexiftController(self.qt);self.c._engine_prepare_timer.stop()
        self.stack.enter_context(patch.object(self.c._korean_activation,'activate'))
        self.c._start_hook(notify=False)
    def tearDown(self):
        c=self.c
        c._engine_prepare_timer.stop();c.tray.hide();c.tray.hide_notification();c.tray.deleteLater()
        if c._window:c._window.hide();c._window.deleteLater()
        if c._ime_toast:c._ime_toast.hide();c._ime_toast.deleteLater()
        c.overlay.deleteLater();c.cursor_indicator.deleteLater();c.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.qt.processEvents()
        self.stack.close();self.folder.cleanup();set_language('ko')
    def test_independent_flags_persist_and_remove_disabled_shortcuts(self):
        c=self.c;c.set_feature_enabled('selector',False)
        self.assertIsNone(c.hook.on_hotkey);self.assertIsNotNone(c.hook.on_ime);self.assertTrue(c.features['zh'])
        c.set_feature_enabled('ja',False);self.mode.release.assert_called_with('ja')
        self.assertIsNone(c.hook.on_ime);self.assertIsNotNone(c.hook.on_chinese)
        c.set_feature_enabled('zh',False)
        self.assertIsNotNone(c.hook.on_traditional)
        c.set_feature_enabled('zh_tw',False)
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
        self.assertEqual(set(c.window.feature_checks),{'selector','ja','zh','zh_tw','tone'})
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
    def test_non_hangul_modes_activate_conversion_and_request_hangul(self):
        c=self.c
        with patch.object(app,'target_is_foreground',return_value=True),patch.object(c._korean_activation,'activate') as activate:
            for conversion in ('ja','zh','zh_tw'):
                self.mode.enabled=False;c._last_ime_toggle=0
                self.mode.toggle.return_value=True
                c._show_ime_panel(123,conversion)
                self.mode.toggle.assert_called_with(conversion)
                activate.assert_called_with(123)

    def test_hangul_allows_toggle_but_off_is_always_available(self):
        c=self.c;c._ime_toast=Mock();c._ime_toast.width.return_value=120;c._ime_toast_timer=Mock()
        self.mode.toggle.return_value=True
        with patch.object(app,'target_is_foreground',return_value=True),patch.object(app,'current_language',return_value=0x412),patch.object(app,'korean_is_hangul',return_value=True) as check:
            c._show_ime_panel(123,'zh')
            check.assert_not_called()
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
    def test_traditional_shortcut_cycles_tw_bopomofo_off_and_restarts(self):
        mode=self.mode;c=self.c
        def toggle(name):
            mode.enabled=not(mode.enabled and mode.language==name)
            mode.language=name;return mode.enabled
        mode.toggle.side_effect=toggle
        with patch.object(app,'target_is_foreground',return_value=True),\
             patch.object(app,'current_language',return_value=app.LANG_KO),\
             patch.object(app,'korean_is_hangul',return_value=True),\
             patch.object(app.time,'monotonic',side_effect=[10,10.1,10.2,10.3]):
            for expected in (('zh_tw',True),('zh_bopomofo',True),('zh_bopomofo',False),('zh_tw',True)):
                c._show_ime_panel(123,'zh_tw')
                self.assertEqual((mode.language,mode.enabled),expected)
        self.assertEqual([call.args[0] for call in mode.toggle.call_args_list],['zh_tw','zh_bopomofo','zh_bopomofo','zh_tw'])
        self.assertIn('ON',c._ime_toast.text())

    def test_traditional_activates_from_english_and_off_remains_available(self):
        c=self.c
        self.mode.toggle.return_value=True
        with patch.object(app,'target_is_foreground',return_value=True),patch.object(c._korean_activation,'activate') as activate:
            c._show_ime_panel(123,'zh_tw')
            activate.assert_called_once_with(123)
        self.mode.toggle.assert_called_once_with('zh_tw');self.mode.toggle.reset_mock()
        self.mode.enabled=True;self.mode.language='zh_bopomofo';self.mode.toggle.return_value=False
        c._last_ime_toggle=0;c._show_ime_panel(123,'zh_tw')
        self.mode.toggle.assert_called_once_with('zh_bopomofo')

    def test_traditional_binding_conflicts_disabled_state_and_language_rebuild(self):
        c=self.c;c.window.navigate(2)
        with patch.object(app.QMessageBox,'warning'):
            c.change_traditional_shortcut(c.binding)
        self.assertEqual(c.traditional_binding,HotkeyBinding('caps','T'))
        c.change_traditional_shortcut(HotkeyBinding('ctrl_alt','T'))
        self.assertEqual(self.store.value('traditional_hotkey/mode'),'ctrl_alt')
        c.window.traditional_key.setCurrentIndex(c.window.traditional_key.findData('A'))
        c.window.traditional_modifier.setCurrentIndex(c.window.traditional_modifier.findData('caps'))
        self.assertFalse(c.window.traditional_apply.isEnabled())
        c.set_feature_enabled('zh_tw',False);self.assertIsNone(c.hook.on_traditional)
        c.change_language('en')
        self.assertFalse(c.window.feature_checks['zh_tw'].isChecked())
        self.assertEqual(c.window.traditional_modifier.currentData(),'ctrl_alt')
        c._show_ime_panel(123,'zh_tw');self.mode.toggle.assert_not_called()

    def test_traditional_can_turn_off_after_leaving_hangul_before_bopomofo_step(self):
        self.mode.enabled=True;self.mode.language='zh_tw';self.mode.toggle.return_value=False
        with patch.object(app,'target_is_foreground',return_value=True),patch.object(app,'current_language',return_value=0x409):
            self.c._show_ime_panel(123,'zh_tw')
        self.mode.toggle.assert_called_once_with('zh_bopomofo')

    def test_defaults_reset_bindings_atomically_and_replace_unsaved_edits(self):
        c=self.c;c.window.navigate(2)
        # This may be occupied: test the cyclic bindings directly, as loaded settings.
        c.binding=HotkeyBinding('caps','A');c.ime_binding=HotkeyBinding('caps','C');c.chinese_binding=HotkeyBinding('caps','Q')
        c.custom_dictionary.replace([dict(keyword='스미네',text='澄音',language='ja')])
        c.window.dictionary_editor.model.add()
        self.store.setValue('general/sound',False)
        c.features['zh']=False
        with patch.object(app,'startup_enabled',return_value=True),patch.object(app,'set_startup_enabled') as startup:
            c.reset_defaults()
        self.assertEqual((c.binding,c.ime_binding,c.chinese_binding),
                         (HotkeyBinding('caps','Q'),HotkeyBinding('caps','A'),HotkeyBinding('caps','C')))
        self.assertEqual(c.features,dict(selector=True,ja=True,zh=True,zh_tw=True,tone=False))
        self.assertEqual(c.custom_dictionary.entries,[])
        self.assertEqual(c.window.dictionary_editor.model.rows,[])
        self.assertTrue(c.window.sound_notice.isChecked())
        self.assertEqual(c.window.language_combo.currentData(),'ko')
        self.assertEqual(c.window._current_page,2)
        startup.assert_called_once_with(False)
        self.assertTrue(c.slots)

    def test_failed_defaults_reset_restores_settings_and_runtime_bindings(self):
        c=self.c;c.window.navigate(2)
        c.custom_dictionary.replace([dict(keyword='스미네',text='澄音',language='ja')])
        before={key:self.store.value(key) for key in self.store.allKeys()}
        old=(c.binding,c.ime_binding,c.chinese_binding,dict(c.features))
        with patch.object(app,'startup_enabled',return_value=False),patch.object(app,'set_startup_enabled'),\
             patch.object(c.custom_dictionary,'replace',side_effect=OSError('test write failure')),\
             patch.object(app.QMessageBox,'warning'):
            c.reset_defaults()
        self.assertEqual({key:self.store.value(key) for key in self.store.allKeys()},before)
        self.assertEqual((c.binding,c.ime_binding,c.chinese_binding,c.features),old)
        self.assertEqual(c.custom_dictionary.lookup('ja','스미네'),'澄音')

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
    def test_custom_word_uses_its_own_reading_and_retains_other_polyphonic_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            dictionary=CustomDictionary(QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat))
            dictionary.replace([dict(keyword='쉐이',text='谁',language='zh')])
            data={'kana':'shui','candidates':['谁','四'],'readings':['shui','si'],
                  'reading_alternatives':{'谁':['shui','shei'],'四':['si']}}
            answer=dictionary.merge('zh','쉐이',data)
            self.assertEqual(answer['readings'][0],'쉐이')
            self.assertNotIn('谁',answer['reading_alternatives'])
            self.assertEqual(answer['reading_alternatives']['四'],['si'])
            self.assertIn('谁',data['reading_alternatives'])
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
