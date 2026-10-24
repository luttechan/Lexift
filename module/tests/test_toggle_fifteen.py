from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QSettings, QRect, Qt, QEvent, QCoreApplication
from PySide6.QtWidgets import QApplication
import app
from layout_profiles import create_layout, sanitized_slots
from hotkeys_windows import OverlayKeyState
from i18n import set_language


class ToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.stack = ExitStack()
        self.directory = tempfile.TemporaryDirectory()
        self.store = QSettings(str(Path(self.directory.name)/'prefs.ini'), QSettings.Format.IniFormat)
        self.layout = create_layout(0x0412)
        self.slots = [dict(hkl=self.layout.hkl, mode='ko_hangul', name='Korean')]
        self.store.setValue('profiles/slots_json', json.dumps(self.slots))
        self.stack.enter_context(patch.object(app, 'QSettings', return_value=self.store))
        self.stack.enter_context(patch.object(app, 'available_layouts', return_value=[self.layout]))
        self.stack.enter_context(patch.object(app, 'CapsQHook'))
        self.stack.enter_context(patch.object(app, 'OverlayNavigationHook'))
        self.stack.enter_context(patch.object(app.LexiftController,'_warm_keyboard',return_value=False))
        self.stack.enter_context(patch.object(app.LexiftController,'_sound'))
        self.stack.enter_context(patch.object(app.QTimer, 'singleShot'))
        self.keyboard = self.stack.enter_context(patch.object(app, 'keyboard_service')).return_value
        self.controller = app.LexiftController(self.qt)
        self.controller.start(background=True)
        self.controller.tray.showMessage = Mock()

    def tearDown(self):
        c = self.controller
        if c._window:
            c._window.hide(); c._window.deleteLater()
        c.tray.hide(); c.tray.deleteLater()
        c.overlay.hide(); c.overlay.deleteLater()
        c.cursor_indicator.deleteLater(); c.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.qt.processEvents()
        self.stack.close()
        self.directory.cleanup()
        set_language('ko')

    def test_default_on_and_off_releases_hooks_and_cancels_switch(self):
        c = self.controller
        self.assertTrue(c._enabled)
        job, revision = c._job, c.overlay._selection_revision
        c.set_enabled(False)
        self.assertFalse(c._running)
        self.keyboard.close.assert_called_once_with(wait=False)
        c.hook.stop.assert_not_called()
        c.navigation_hook.stop.assert_not_called()
        self.assertGreater(c._job, job)
        self.assertGreater(c.overlay._selection_revision, revision)
        with patch.object(c.overlay, 'open') as show, patch('app.request_hkl') as request:
            c._hotkey(123)
            c.apply_slot(self.slots[0])
        show.assert_not_called(); request.assert_not_called()
        self.assertIn('비활성화', c.tray.showMessage.call_args.args[1])

    def test_reenable_restores_hooks_and_shortcut_notification(self):
        c = self.controller
        c.set_enabled(False); c.set_enabled(True)
        self.assertTrue(c._enabled and c._running)
        self.assertEqual(c.hook.start.call_count, 2)
        self.assertEqual(c.navigation_hook.start.call_count, 2)
        self.assertIn(c.binding.title, c.tray.showMessage.call_args.args[1])

    def test_tray_and_dashboard_toggles_stay_synchronized(self):
        c = self.controller
        c.toggle_action.setChecked(False)
        self.assertEqual(c.window.enabled_button.text(), 'OFF')
        self.assertFalse(c.window.selector_button.isEnabled())
        c.window.enabled_button.click()
        self.assertTrue(c.toggle_action.isChecked())
        self.assertEqual(c.window.enabled_button.text(), 'ON')

    def test_off_survives_language_change_and_fifteen_slot_save(self):
        c = self.controller
        c.set_enabled(False)
        c.change_language('en')
        c.save_slots([{**self.slots[0], 'name':str(i)} for i in range(15)])
        self.assertFalse(c._enabled)
        self.assertEqual(c.window.enabled_button.text(), 'OFF')
        self.assertEqual(len(json.loads(self.store.value('profiles/slots_json'))),15)
        self.assertEqual(c.hook.start.call_count, 1)

    def test_delayed_start_notice_never_reports_on_after_off(self):
        c = self.controller
        c.set_enabled(False); c.tray.showMessage.reset_mock()
        c._notify_active()
        c.tray.showMessage.assert_not_called()

    def test_failed_resume_returns_toggle_to_off(self):
        c = self.controller
        c.set_enabled(False)
        c.hook.start.side_effect = RuntimeError('registration failed')
        with patch.object(app.QMessageBox, 'warning'):
            c.set_enabled(True)
        self.assertFalse(c._enabled)
        self.assertFalse(c.toggle_action.isChecked())


class FifteenSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layout = create_layout(0x0412)
        self.slots = [dict(hkl=self.layout.hkl, mode='ko_hangul', name=f'Slot {i}') for i in range(15)]
        self.layouts = patch.object(app, 'available_layouts', return_value=[self.layout])
        self.layouts.start()
        self.overlay = app.Overlay()

    def tearDown(self):
        self.overlay.hide(); self.overlay.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.qt.processEvents(); self.layouts.stop()

    def test_fifteen_profiles_preserved_and_extra_profiles_bounded(self):
        self.assertEqual(sanitized_slots(self.slots), self.slots)
        self.assertEqual(len(sanitized_slots(self.slots*2)), 15)

    def test_all_fifteen_direct_keys_choose_correct_slots(self):
        self.overlay.rebuild(self.slots)
        with patch.object(self.overlay, '_activate') as activate:
            for index, key in enumerate(app.SELECTION_KEYS):
                self.overlay._handle_key(Qt.Key(ord(key)))
                self.assertEqual(activate.call_args.args[0], self.slots[index])

    def test_numpad_zero_selects_tenth_slot(self):
        self.overlay.rebuild(self.slots)
        with patch.object(self.overlay, 'isVisible', return_value=True), patch.object(self.overlay,'_activate') as activate:
            self.overlay.navigate_virtual_key(0x60)
        self.assertEqual(activate.call_args.args[0], self.slots[9])

    def test_small_screen_uses_scroll_and_cached_tiles(self):
        screen = Mock(); screen.availableGeometry.return_value = QRect(0,0,1024,600)
        with patch.object(app.QApplication, 'screenAt', return_value=screen):
            self.overlay.rebuild(self.slots)
            previous = list(self.overlay.tiles)
            self.overlay.rebuild(self.slots)
        self.assertEqual(previous, self.overlay.tiles)
        self.assertLessEqual(self.overlay.height(),576)
        self.assertLessEqual(self.overlay.width(),1000)
        self.assertGreater(self.overlay.grid_host.minimumHeight(),self.overlay.height()-173)
        self.overlay.ensurePolished()
        self.overlay.layout().activate()
        self.overlay.grab()
        self.overlay._highlight(14)
        self.assertGreater(self.overlay.grid_scroll.verticalScrollBar().value(), 0)

    def test_extended_hook_keys_balanced_and_disabled_keys_pass_through(self):
        state = OverlayKeyState()
        for key in '7890ABCDE':
            vk = ord(key)
            self.assertEqual(state.handle(vk,True,False),(False,False))
            self.assertEqual(state.handle(vk,True,True),(True,True))
            self.assertEqual(state.handle(vk,False,False),(True,False))
            self.assertEqual(state.handle(vk,True,True,modified=True),(False,False))

    def test_editor_handles_stale_events_after_last_row_deleted(self):
        editor = app.SlotEditor(self.slots)
        editor.delete_slot(14)
        editor.delete_slot(14)
        editor.move_slot(14, -1)
        editor._select_mode(14, 'ko_latin')
        editor._select_layout(14, self.layout.hkl)
        editor._set_name(14, 'stale')
        self.assertEqual(len(editor.slots), 14)
        self.assertEqual(editor.slots[-1], self.slots[13])
        editor.deleteLater()
