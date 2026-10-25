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
            native=Path(__file__).with_name('lexift_keyboard.exe')
            if native.is_file():
                command=[str(native),str(listener.getsockname()[1]),token]
            elif getattr(sys, 'frozen', False):
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
                    self.reader = threading.Thread(target=self._read, args=(connection, self.pending), daemon=True, name='Lexift-HookEvents')
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
                                       daemon=True, name='Lexift-HookCommands')
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
                elif connection is self.connection and message.get('event') == 'hotkey' and caps and caps.on_hotkey:
                    caps.on_hotkey(int(message['hwnd']))
                elif connection is self.connection and message.get('event') == 'ime' and caps and caps.on_ime:
                    caps.on_ime(int(message['hwnd']))
                elif connection is self.connection and message.get('event') == 'chinese' and caps and caps.on_chinese:
                    caps.on_chinese(int(message['hwnd']))
                elif connection is self.connection and message.get('event') == 'traditional' and caps and caps.on_traditional:
                    caps.on_traditional(int(message['hwnd']))
                elif connection is self.connection and message.get('event') == 'tone' and caps and caps.on_tone:
                    caps.on_tone(int(message['hwnd']),int(message['tone']))
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
            threading.Thread(target=reap, name='Lexift-HookShutdown', daemon=False).start()


_shared = None


def existing_worker_process():
    """Observe the already-owned worker without starting it or sending IPC."""
    return _shared.process if _shared is not None else None


def service():
    global _shared
    if _shared is None:
        _shared = HookService()
    return _shared


class CapsQHook:
    def __init__(self, on_hotkey, binding=None, on_ime=None, ime_binding=None, on_chinese=None, chinese_binding=None,on_traditional=None,traditional_binding=None,on_tone=None):
        from hotkeys_windows import HotkeyBinding
        self.on_hotkey = on_hotkey
        self.on_ime = on_ime
        self.on_chinese = on_chinese
        self.chinese_binding = chinese_binding or HotkeyBinding('caps', 'C')
        self.on_traditional=on_traditional
        self.on_tone=on_tone
        self.traditional_binding=traditional_binding or HotkeyBinding('caps','T')
        self.ime_binding = ime_binding or HotkeyBinding('caps', 'A')
        self.binding = binding or HotkeyBinding()
        self.thread = None

    def start(self):
        worker = service()
        worker.caps = self
        extra = {'ime': True} if self.on_ime else {}
        if self.on_hotkey is None:extra['selector']=False
        if self.on_ime:
            extra.update(ime_mode=self.ime_binding.mode, ime_key=self.ime_binding.key)
        if self.on_chinese:
            extra.update(chinese=True, chinese_mode=self.chinese_binding.mode, chinese_key=self.chinese_binding.key)
        if self.on_traditional:
            extra.update(traditional=True,traditional_mode=self.traditional_binding.mode,traditional_key=self.traditional_binding.key)
        if self.on_tone:extra['tones']=True
        worker.command('caps-start', mode=self.binding.mode, key=self.binding.key, **extra)
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

    def set_active(self, active, target=0):
        worker = service()
        if worker.navigation is self and worker.connection:
            extra={'target':int(target)} if int(active) in (2,3) else {}
            worker.command('active', wait=False, active=int(active), **extra)

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
    ime_caps = None
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
                        if ime_caps:
                            ime_caps.stop()
                            ime_caps = None
                        from hotkeys_windows import HotkeyGroup
                        entries=[]
                        if message.get('selector',True):
                            entries.append((HotkeyBinding(message['mode'],message['key']),
                                  lambda _:events.put(dict(event='hotkey',hwnd=get_target_window()))))
                        if message.get('ime'):
                            entries.append((HotkeyBinding(message.get('ime_mode','caps'),message.get('ime_key','A')),
                                            lambda _:events.put(dict(event='ime',hwnd=get_target_window()))))
                        if message.get('chinese'):
                            entries.append((HotkeyBinding(message.get('chinese_mode','caps'),message.get('chinese_key','C')),
                                            lambda _:events.put(dict(event='chinese',hwnd=get_target_window()))))
                        if message.get('traditional'):
                            entries.append((HotkeyBinding(message.get('traditional_mode','caps'),message.get('traditional_key','T')),
                                            lambda _:events.put(dict(event='traditional',hwnd=get_target_window()))))
                        cycle=(HotkeyBinding(message.get('traditional_mode','caps'),message.get('traditional_key','T'))
                               if message.get('traditional') else None)
                        caps=HotkeyGroup(entries,cycle_binding=cycle,on_tone=(lambda _,tone:events.put(dict(event='tone',hwnd=get_target_window(),tone=tone))) if message.get('tones') else None)
                        caps.start()
                    elif operation == 'caps-stop':
                        if ime_caps:
                            ime_caps.stop()
                            ime_caps = None
                        if caps:
                            caps.stop()
                            caps = None
                    elif operation == 'navigation-start':
                        navigation.start()
                    elif operation == 'navigation-stop':
                        navigation.stop()
                    elif operation == 'active':
                        navigation.set_active(message['active'], message.get('target',0))
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
            if ime_caps:
                ime_caps.stop()
            if caps:
                caps.stop()
            events.put(None)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--hook-worker':
        raise SystemExit(2)
    raise SystemExit(run_worker(sys.argv[2], sys.argv[3]))
