"""Two Caps chords share suppression; IME events stay outside hook callbacks."""
import ctypes
from ctypes import wintypes
import socket
import unittest
from unittest.mock import Mock, patch

from native_hooks import library
from tests.test_native_hooks import CapsState
import isolated_hotkeys as hooks
from ime_panel import CandidatePanel


class ImeShortcutTests(unittest.TestCase):
    def setUp(self):
        self.dll = library()
        self.dll.ks_caps_multi_step.argtypes = [ctypes.POINTER(CapsState), ctypes.POINTER(wintypes.DWORD),
                                               wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.dll.ks_caps_multi_step.restype = wintypes.DWORD
        self.state = CapsState(0x51, 0, 0, 0, 0)
        self.secondary = wintypes.DWORD()

    def step(self, key, down):
        return self.dll.ks_caps_multi_step(ctypes.byref(self.state), ctypes.byref(self.secondary), key, down, 0x41)

    def test_caps_a_once_and_balanced_when_caps_released_first(self):
        self.assertEqual(self.step(0x14, True), 1)
        self.assertEqual(self.step(0x41, True), 9)
        self.assertEqual(self.step(0x41, True), 1)  # auto repeat
        self.assertEqual(self.step(0x14, False), 1)  # no Caps toggle
        self.assertEqual(self.step(0x41, False), 1)
        self.assertEqual(self.step(0x41, True), 0)  # ordinary typing restored
        self.assertEqual(self.step(0x41, False), 0)

    def test_caps_q_still_opens_selector_and_does_not_also_open_ime(self):
        actions = [self.step(key, down) for key, down in
                   [(0x14,True),(0x51,True),(0x41,True),(0x51,False),(0x41,False),(0x14,False)]]
        self.assertEqual(sum(bool(a & 2) for a in actions), 1)
        self.assertEqual(sum(bool(a & 8) for a in actions), 0)
        self.assertFalse(any(a & 4 for a in actions))

    def test_ime_chord_then_q_does_not_open_selector(self):
        actions = [self.step(key, down) for key, down in
                   [(0x14,True),(0x41,True),(0x51,True),(0x41,False),(0x51,False),(0x14,False)]]
        self.assertEqual(sum(bool(a & 8) for a in actions), 1)
        self.assertEqual(sum(bool(a & 2) for a in actions), 0)
        self.assertFalse(any(a & 4 for a in actions))

    def test_plain_caps_tap_and_ordinary_caps_chord_keep_replay_behavior(self):
        self.assertEqual(self.step(0x14, True), 1)
        self.assertEqual(self.step(0x14, False), 5)
        self.step(0x14, True)
        self.assertEqual(self.step(0x5A, True), 4)
        self.assertEqual(self.step(0x41, True), 0)

    def test_ipc_ime_event_does_not_call_selector_callback(self):
        first, second = socket.socketpair()
        worker = hooks.HookService()
        primary, ime = Mock(), Mock()
        worker.connection = second
        worker.caps = hooks.CapsQHook(primary, on_ime=ime)
        try:
            first.sendall(b'{"event":"ime","hwnd":12345}\n')
            first.shutdown(socket.SHUT_WR)
            worker._read(second)
            ime.assert_called_once_with(12345)
            primary.assert_not_called()
        finally:
            worker.connection = None
            first.close(); second.close()

    def test_repeated_shortcut_turns_panel_off(self):
        panel = CandidatePanel()
        panel.window = Mock()
        panel.window.isVisible.side_effect = [True, False]
        self.assertFalse(panel.toggle())
        panel.window.hide.assert_called_once()

    def test_proxy_enables_second_chord_in_owned_worker(self):
        worker = Mock()
        with patch.object(hooks, 'service', return_value=worker):
            proxy = hooks.CapsQHook(Mock(), on_ime=Mock())
            proxy.start()
            worker.command.assert_called_once_with('caps-start', mode='caps', key='Q', ime=True, ime_mode='caps', ime_key='A')
