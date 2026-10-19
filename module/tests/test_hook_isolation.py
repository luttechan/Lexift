import json
import socket
import threading
import time
import subprocess
import unittest
from unittest.mock import Mock, patch

import isolated_hotkeys as hooks
from hotkeys_windows import HotkeyBinding


class HookIsolationTests(unittest.TestCase):
    def test_visibility_update_returns_even_when_socket_writer_is_stalled(self):
        worker = hooks.HookService()
        entered, release = threading.Event(), threading.Event()
        connection = Mock()
        def stalled_write(data):
            entered.set()
            release.wait(2)
        connection.sendall.side_effect = stalled_write
        worker.connection = connection
        worker.process = Mock()
        worker.process.poll.return_value = None
        try:
            started = time.perf_counter()
            worker.command('active', wait=False, active=True)
            self.assertLess(time.perf_counter() - started, .2)
            self.assertTrue(entered.wait(1))
            # Even a second update cannot wait behind sendall().
            started = time.perf_counter()
            worker.command('active', wait=False, active=False)
            self.assertLess(time.perf_counter() - started, .2)
        finally:
            release.set()
            worker.close()

    def test_old_connection_cannot_fail_new_commands_or_deliver_old_hotkeys(self):
        worker = hooks.HookService()
        first, second = socket.socketpair()
        old_pending = {}
        event = threading.Event()
        worker.pending = {7: (event, [])}
        worker.connection = Mock()
        worker.caps = hooks.CapsQHook(Mock())
        try:
            first.sendall(b'{"event":"hotkey","hwnd":12345}\n')
            first.shutdown(socket.SHUT_WR)
            worker._read(second, old_pending)
            self.assertFalse(event.is_set())
            worker.caps.on_hotkey.assert_not_called()
        finally:
            worker.connection = None
            first.close(); second.close()
            worker.close()

    def test_send_failure_wakes_waiter_and_clears_pending_command(self):
        first, second = socket.socketpair()
        worker = hooks.HookService()
        worker.connection = first
        worker.ensure_started = Mock()
        worker.reader = threading.Thread(target=worker._read, args=(first,), daemon=True)
        worker.reader.start()
        try:
            with patch.object(hooks, 'send', side_effect=OSError('connection broken')):
                started = time.perf_counter()
                with self.assertRaisesRegex(RuntimeError, 'disconnected'):
                    worker.command('caps-start')
                self.assertLess(time.perf_counter()-started, 1)
            self.assertFalse(worker.pending)
        finally:
            worker.close(); second.close()

    def test_visibility_update_never_restarts_dead_worker(self):
        worker = hooks.HookService()
        worker.process = Mock()
        worker.process.poll.return_value = 0
        worker.connection = Mock()
        with patch.object(worker, 'ensure_started', side_effect=AssertionError('synchronous startup')):
            worker.command('active', wait=False, active=False)
        worker.connection.sendall.assert_not_called()
        worker.connection = None

    def test_shutdown_returns_while_unresponsive_worker_is_reaped(self):
        worker = hooks.HookService()
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        process = Mock()
        process.poll.return_value = None
        def wait(timeout):
            entered.set()
            if timeout == .25:
                release.wait(2)
                raise subprocess.TimeoutExpired('owned-worker', timeout)
            finished.set()
            return 0
        process.wait.side_effect = wait
        worker.process = process
        first, second = socket.socketpair()
        worker.connection = first
        started = time.monotonic()
        try:
            worker.close(wait=False)
            self.assertLess(time.monotonic() - started, .2)
            self.assertTrue(entered.wait(1))
            self.assertFalse(finished.is_set())
            self.assertIsNone(worker.process)
            self.assertIsNone(worker.connection)
            second.settimeout(.2)
            self.assertEqual(second.recv(1), b'')
            worker.close()  # The atexit fallback must not repeat the wait.
        finally:
            release.set()
            second.close()
        self.assertTrue(finished.wait(2))
        process.terminate.assert_called_once()

    def test_protocol_handles_split_and_combined_messages(self):
        first, second = socket.socketpair()
        try:
            first.sendall(b'{"event":"hot')
            first.sendall(b'key"}\n{"id":2}\n')
            first.shutdown(socket.SHUT_WR)
            self.assertEqual(list(hooks.messages(second)), [{'event':'hotkey'}, {'id':2}])
        finally:
            first.close(); second.close()

    def test_hotkey_preserves_captured_target_window(self):
        first, second = socket.socketpair()
        worker = hooks.HookService()
        callback = Mock()
        worker.connection = second
        worker.caps = hooks.CapsQHook(callback)
        first.sendall(b'{"event":"hotkey","hwnd":12345}\n')
        first.shutdown(socket.SHUT_WR)
        worker._read(second)
        callback.assert_called_once_with(12345)
        first.close(); second.close()

    def test_registration_failure_is_reported_to_caller(self):
        first, second = socket.socketpair()
        worker = hooks.HookService()
        worker.connection = first
        worker.ensure_started = Mock()
        worker.reader = threading.Thread(target=worker._read, args=(first,), daemon=True)
        worker.reader.start()
        def reject():
            command = next(hooks.messages(second))
            hooks.send(second, {'id':command['id'], 'error':'Shortcut already in use'})
        responder = threading.Thread(target=reject)
        responder.start()
        try:
            with self.assertRaisesRegex(RuntimeError, 'Shortcut already in use'):
                worker.command('caps-start')
            self.assertFalse(worker.pending)
        finally:
            responder.join()
            worker.close(); second.close()

    def test_proxy_forwards_binding_and_does_not_register_in_gui(self):
        worker = Mock()
        with patch.object(hooks, 'service', return_value=worker):
            proxy = hooks.CapsQHook(lambda hwnd: None, HotkeyBinding('ctrl_shift','F12'))
            proxy.start()
            worker.command.assert_called_once_with('caps-start', mode='ctrl_shift', key='F12')
            self.assertIs(proxy.thread, worker.reader)

    def test_navigation_visibility_is_sent_without_waiting_for_gui_ack(self):
        worker = Mock()
        with patch.object(hooks, 'service', return_value=worker):
            proxy = hooks.OverlayNavigationHook(lambda key: None)
            worker.navigation = proxy
            proxy.set_active(True)
            worker.command.assert_called_once_with('active', wait=False, active=True)
