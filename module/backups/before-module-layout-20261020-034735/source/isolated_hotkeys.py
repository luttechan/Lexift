"""Global Windows hooks must never wait for the GUI process's Python GIL."""
from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import subprocess
import sys
import threading
import time


def send(stream, value):
    stream.sendall((json.dumps(value) + '\n').encode('utf-8'))


def messages(stream):
    buffered = b''
    while True:
        block = stream.recv(4096)
        if not block:
            return
        buffered += block
        if len(buffered) > 16384:
            raise RuntimeError('Invalid hook message')
        while b'\n' in buffered:
            line, buffered = buffered.split(b'\n', 1)
            yield json.loads(line)


class HookService:
    def __init__(self):
        self.process = None
        self.connection = None
        self.reader = None
        self.writer = None
        self.outgoing = None
        self._bad_connection = None
        self.lock = threading.Lock()
        self.pending = {}
        self.sequence = 0
        self.caps = None
        self.navigation = None
        atexit.register(self.close)

    def ensure_started(self):
        if (self.process is not None and self.process.poll() is None and self.connection
                and self._bad_connection is not self.connection):
            return
        navigation_to_restore = (self.navigation if self.navigation is not None
                                 and self.navigation.thread is not None else None)
        self.close()
        token = secrets.token_hex(32)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(4)
            listener.settimeout(.25)
            args = ['--hook-worker', str(listener.getsockname()[1]), token]
            if getattr(sys, 'frozen', False):
                command = [sys.executable, *args]
            else:
                command = [sys.executable, '-E', '-s', str(Path(__file__).resolve()), *args]
            environment = os.environ.copy()
            environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
            self.process = subprocess.Popen(command, env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 8
            try:
                while time.monotonic() < deadline:
                    if self.process.poll() is not None:
                        raise RuntimeError('Keyboard worker could not start')
                    try:
                        connection, _ = listener.accept()
                    except socket.timeout:
                        continue
                    connection.settimeout(1)
                    try:
                        hello = next(messages(connection))
                        if hello != {'token': token}:
                            connection.close()
                            continue
                    except (OSError, ValueError, StopIteration):
                        connection.close()
                        continue
                    connection.settimeout(None)
                    connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    self.connection = connection
                    self._bad_connection = None
                    self._start_writer(connection)
                    self.reader = threading.Thread(target=self._read, args=(connection, self.pending), daemon=True, name='KanaShift-HookEvents')
                    self.reader.start()
                    if navigation_to_restore is not None:
                        navigation_to_restore.start()
                    return
                raise RuntimeError('Keyboard worker startup timed out')
            except Exception:
                self.close()
                raise

    def _start_writer(self, connection):
        self.outgoing = queue.SimpleQueue()
        self.writer = threading.Thread(target=self._write, args=(connection, self.outgoing, self.pending),
                                       daemon=True, name='KanaShift-HookCommands')
        self.writer.start()

    def _write(self, connection, outgoing, pending_commands):
        try:
            while True:
                message = outgoing.get()
                if message is None:
                    return
                send(connection, message)
        except OSError:
            self._fail_connection(connection, pending_commands)
            # Wake the worker too; Windows recv() may not return immediately
            # for a local shutdown, so acknowledgements were released above.
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _fail_connection(self, connection, pending_commands):
        with self.lock:
            if connection is self.connection:
                self._bad_connection = connection
            for event, result in list(pending_commands.values()):
                result.append('Keyboard worker disconnected')
                event.set()

    def _read(self, connection, pending_commands=None):
        if pending_commands is None:
            pending_commands = self.pending
        try:
            for message in messages(connection):
                if not isinstance(message, dict):
                    raise ValueError('Invalid hook message')
                caps, navigation = self.caps, self.navigation
                if 'id' in message:
                    pending = pending_commands.get(message['id'])
                    if pending:
                        pending[1].append(message.get('error'))
                        pending[0].set()
                elif connection is self.connection and message.get('event') == 'hotkey' and caps:
                    caps.on_hotkey(int(message['hwnd']))
                elif connection is self.connection and message.get('event') == 'navigation' and navigation:
                    navigation.on_key(int(message['key']))
        except (OSError, ValueError, TypeError, RuntimeError):
            pass
        finally:
            self._fail_connection(connection, pending_commands)

    def command(self, operation, wait=True, **data):
        if wait:
            self.ensure_started()
        elif (not self.connection or not self.process or self.process.poll() is not None
              or self._bad_connection is self.connection):
            return  # Visibility updates must never start/restart a worker.
        pending_commands = self.pending
        with self.lock:
            if not self.connection or self._bad_connection is self.connection:
                raise RuntimeError('Keyboard worker disconnected')
            if self.outgoing is None:
                self._start_writer(self.connection)
            self.sequence += 1
            number = self.sequence
            event, result = threading.Event(), []
            if wait:
                pending_commands[number] = (event, result)
            self.outgoing.put(dict(id=number, operation=operation, **data))
        if wait:
            try:
                if not event.wait(6):
                    raise RuntimeError('Keyboard worker did not respond')
                if result and result[0]:
                    raise RuntimeError(result[0])
            finally:
                pending_commands.pop(number, None)

    def close(self, *, wait=True):
        with self.lock:
            connection, process, reader, writer = self.connection, self.process, self.reader, self.writer
            outgoing, pending = self.outgoing, self.pending
            self.connection = None
            self._bad_connection = None
            self.process = None
            self.reader = None
            self.writer = None
            self.outgoing = None
            self.pending = {}
        for event, result in list(pending.values()):
            result.append('Keyboard worker disconnected')
            event.set()
        if outgoing is not None:
            outgoing.put(None)
        if connection:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        def reap():
            try:
                if process and process.poll() is None:
                    try:
                        process.wait(timeout=3 if wait else .25)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=3)
                if reader and reader is not threading.current_thread():
                    reader.join(timeout=1)
                if writer and writer is not threading.current_thread():
                    writer.join(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                if process and process.poll() is None:
                    process.kill()

        if wait:
            reap()
        elif process or reader or writer:
            # Keep the reaper alive until our owned worker exits, without
            # waiting for hook acknowledgements on the GUI thread.
            threading.Thread(target=reap, name='KanaShift-HookShutdown', daemon=False).start()


_shared = None


def service():
    global _shared
    if _shared is None:
        _shared = HookService()
    return _shared


class CapsQHook:
    def __init__(self, on_hotkey, binding=None):
        from hotkeys_windows import HotkeyBinding
        self.on_hotkey = on_hotkey
        self.binding = binding or HotkeyBinding()
        self.thread = None

    def start(self):
        worker = service()
        worker.caps = self
        worker.command('caps-start', mode=self.binding.mode, key=self.binding.key)
        self.thread = worker.reader

    def stop(self):
        worker = service()
        try:
            if worker.caps is self and worker.process and worker.process.poll() is None:
                worker.command('caps-stop')
        finally:
            if worker.caps is self:
                worker.caps = None
            self.thread = None
            if worker.navigation is None:
                worker.close()


class OverlayNavigationHook:
    def __init__(self, on_key):
        self.on_key = on_key
        self.thread = None

    def start(self):
        worker = service()
        worker.navigation = self
        worker.command('navigation-start')
        self.thread = worker.reader

    def set_active(self, active):
        worker = service()
        if worker.navigation is self and worker.connection:
            worker.command('active', wait=False, active=bool(active))

    def stop(self):
        worker = service()
        try:
            if worker.navigation is self and worker.process and worker.process.poll() is None:
                worker.command('navigation-stop')
        finally:
            if worker.navigation is self:
                worker.navigation = None
            self.thread = None
            if worker.caps is None:
                worker.close()


def run_worker(port, token):
    from hotkeys_windows import CapsQHook as NativeCaps, OverlayNavigationHook as NativeNavigation, HotkeyBinding
    from ime_windows import get_target_window
    events = queue.SimpleQueue()
    caps = None
    navigation = NativeNavigation(lambda key: events.put(dict(event='navigation', key=key)))
    with socket.create_connection(('127.0.0.1', int(port)), timeout=8) as connection:
        connection.settimeout(None)
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        send(connection, {'token': token})
        disconnected = threading.Event()

        def writer():
            try:
                while True:
                    message = events.get()
                    if message is None:
                        return
                    send(connection, message)
            except OSError:
                disconnected.set()
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            for message in messages(connection):
                error = None
                try:
                    operation = message['operation']
                    if operation == 'caps-start':
                        if caps:
                            caps.stop()
                        caps = NativeCaps(lambda _: events.put(dict(event='hotkey', hwnd=get_target_window())),
                                          HotkeyBinding(message['mode'], message['key']))
                        caps.start()
                    elif operation == 'caps-stop':
                        if caps:
                            caps.stop()
                            caps = None
                    elif operation == 'navigation-start':
                        navigation.start()
                    elif operation == 'navigation-stop':
                        navigation.stop()
                    elif operation == 'active':
                        navigation.set_active(message['active'])
                    else:
                        raise RuntimeError('Invalid keyboard command')
                except Exception as exception:
                    error = str(exception)
                events.put(dict(id=message['id'], error=error))
        except OSError:
            # Windows may report socket shutdown as a reset instead of EOF.
            # The parent owns this connection; either means normal shutdown.
            pass
        finally:
            navigation.stop()
            if caps:
                caps.stop()
            events.put(None)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--hook-worker':
        raise SystemExit(2)
    raise SystemExit(run_worker(sys.argv[2], sys.argv[3]))
