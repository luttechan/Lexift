"""On-demand diagnostics. No process enumeration, IPC, history, or startup work."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import threading
import time
import weakref

from PySide6.QtCore import QObject, QEvent, Qt, QTimer, Signal, Slot, qVersion
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QToolButton, QVBoxLayout, QWidget
from i18n import tr, text_font_family
from isolated_hotkeys import existing_worker_process


class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD),
                *[(name, ctypes.c_size_t) for name in (
                    'peak_ws', 'working_set', 'peak_paged', 'paged', 'peak_nonpaged',
                    'nonpaged', 'pagefile', 'peak_pagefile', 'private')]]


class NativeReader:
    def __init__(self, worker_provider=existing_worker_process):
        self.worker_provider = worker_provider
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GetCurrentProcess.restype = ctypes.c_void_p
        self.handle = self.kernel.GetCurrentProcess()
        self.query = self.kernel.K32GetProcessMemoryInfo
        self.query.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
        self.query.restype = wintypes.BOOL
        self.counters = MemoryCounters()
        self.counters.cb = ctypes.sizeof(self.counters)
        # Calculate once from process creation time; the displayed age does not
        # reset when About is opened or when the system clock changes later.
        times = [wintypes.FILETIME() for _ in range(4)]
        self.kernel.GetProcessTimes.argtypes = [ctypes.c_void_p, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
        age = 0.0
        if self.kernel.GetProcessTimes(self.handle, *(ctypes.byref(t) for t in times)):
            ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            age = max(0.0, time.time() - (ticks / 10_000_000 - 11_644_473_600))
        self.started = time.monotonic() - age

    def _memory(self, handle):
        if not handle or not self.query(handle, ctypes.byref(self.counters), self.counters.cb):
            return None, None
        return self.counters.working_set, self.counters.private

    def read(self):
        main, private = self._memory(self.handle)
        worker = self.worker_provider()
        # Holding this Popen reference keeps its existing Windows handle alive
        # even if OFF/shutdown simultaneously detaches it from HookService.
        handle = getattr(worker, '_handle', None) if worker is not None else None
        child, _ = self._memory(int(handle)) if handle is not None else (None, None)
        return main, private, child, max(0, int(time.monotonic() - self.started))


class Events(QObject):
    sampled = Signal(int, object)


class Sampler:
    """One bounded worker, asleep off-screen; never joined by the GUI thread."""
    def __init__(self, events, interval=2.0, reader_factory=NativeReader):
        self.events = weakref.ref(events)
        self.interval = interval
        self.reader_factory = reader_factory
        self.condition = threading.Condition()
        self.active = False
        self.closed = False
        self.generation = 0
        self.thread = None
        self.latest = None
        self.pending = False

    def set_active(self, active):
        with self.condition:
            if self.closed or self.active == active:
                return self.generation
            self.active = active
            self.generation += 1
            self.latest = None
            self.pending = False
            if active and self.thread is None:
                self.thread = threading.Thread(target=self._run, name='Lexift-Diagnostics', daemon=True)
                self.thread.start()
            self.condition.notify_all()
            return self.generation

    def take(self, generation):
        with self.condition:
            if self.latest is None or self.latest[0] != generation:
                return None
            self.pending = False
            return self.latest[1]

    def close(self):
        with self.condition:
            self.closed = True
            self.active = False
            self.latest = None
            self.pending = False
            self.condition.notify_all()

    def _run(self):
        reader = None
        while True:
            with self.condition:
                while not self.active and not self.closed:
                    self.condition.wait()
                if self.closed:
                    return
                generation = self.generation
            try:
                if reader is None:
                    reader = self.reader_factory()
                sample = reader.read()
            except Exception:
                sample = (None, None, None, None)
            with self.condition:
                if self.closed:
                    return
                if not self.active or generation != self.generation:
                    continue
                self.latest = generation, sample
                notify = not self.pending
                self.pending = True
            if notify:
                target = self.events()
                if target is None:
                    return
                try:
                    target.sampled.emit(generation, None)
                except RuntimeError:  # QObject was destroyed while sampling.
                    return
                del target
            with self.condition:
                if self.active and not self.closed and generation == self.generation:
                    self.condition.wait(self.interval)


def _label(text, kind=''):
    item = QLabel(text)
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setWordWrap(True)
    item.setObjectName(kind)
    family = text_font_family(text)
    if family != 'Malgun Gothic':
        item.setStyleSheet(f'font-family:"{family}";')
    return item


class RuntimeStatsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('panel')
        self._sampling = False
        self._generation = 0
        self._watched_window = None
        self._events = Events(self)
        self._sampler = Sampler(self._events)
        self._events.sampled.connect(self._on_sample, Qt.ConnectionType.QueuedConnection)
        # The destruction callback owns only the plain sampler, not this widget.
        self.destroyed.connect(lambda *_args, sampler=self._sampler: sampler.close())
        self._visibility = QTimer(self)
        self._visibility.setSingleShot(True)
        self._visibility.timeout.connect(self._sync_visibility)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(26, 22, 26, 22)
        self._outer.setSpacing(12)
        self.toggle = QToolButton(self)
        self.toggle.setText(tr('실행 정보'))
        self.toggle.setCheckable(True)
        self.toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setStyleSheet('QToolButton { border:0; font-weight:700; padding:0; }')
        self.toggle.toggled.connect(self._set_expanded)
        self._outer.addWidget(self.toggle)
        self.details = None
        self.values = []

    def _set_expanded(self, expanded):
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        if expanded:
            self._create_details()
            self._schedule_visibility()
        else:
            # Pause synchronously; queued samples cannot repaint deleted labels.
            self._sampling = False
            self._generation = self._sampler.set_active(False)
            if self.details is not None:
                self.details.hide()
                self._outer.removeWidget(self.details)
                self.details.deleteLater()
                self.details = None
                self.values = []

    def _create_details(self):
        if self.details is not None:
            return
        self.details = QWidget(self)
        outer = QVBoxLayout(self.details)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        self.values = []
        for row, key in enumerate(('RAM / 본체', 'RAM / 단축키 보조', '전용 메모리 / 본체',
                                   '가동 시간', '실행 환경', '런타임')):
            grid.addWidget(_label(tr(key), 'muted'), row, 0)
            value = _label('—')
            value.setMinimumWidth(130)
            grid.addWidget(value, row, 1)
            self.values.append(value)
        version = sys.getwindowsversion()
        windows = '11' if version.build >= 22000 else str(version.major)
        mode = tr('EXE 배포본') if getattr(sys, 'frozen', False) else tr('Python 소스')
        bits = ctypes.sizeof(ctypes.c_void_p) * 8
        self.values[4].setText(f'Windows {windows} ({version.build}) / x{bits if bits == 64 else 86} / {mode}')
        self.values[5].setText(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} / Qt {qVersion()}')
        outer.addLayout(grid)
        outer.addWidget(_label(tr('2초 간격 / 화면에 보일 때만 갱신'), 'small'))
        self.values[0].setToolTip(tr('현재 물리 메모리 사용량입니다. 공유 메모리가 포함됩니다.'))
        self.values[1].setToolTip(tr('단축키 보조 프로세스만 표시합니다. 실행 중이 아니면 —로 표시됩니다.'))
        self.values[2].setToolTip(tr('프로세스 전용 커밋 메모리입니다. 물리 RAM 사용량과 다를 수 있습니다.'))
        self._outer.addWidget(self.details)
        self.details.show()

    def watch_viewport(self, scroll):
        scroll.viewport().installEventFilter(self)
        scroll.verticalScrollBar().valueChanged.connect(self._schedule_visibility)
        scroll.verticalScrollBar().rangeChanged.connect(self._schedule_visibility)

    def _schedule_visibility(self, *_):
        if not self._visibility.isActive():
            self._visibility.start(0)

    def eventFilter(self, watched, event):
        if self.isVisible() and event.type() in (QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.Resize,
                             QEvent.Type.Paint, QEvent.Type.WindowStateChange):
            self._schedule_visibility()
        return False

    def showEvent(self, event):
        super().showEvent(event)
        window = self.window()
        if self._watched_window is not window:
            if self._watched_window is not None:
                self._watched_window.removeEventFilter(self)
            self._watched_window = window
            window.installEventFilter(self)
        self._schedule_visibility()

    def hideEvent(self, event):
        self._sampling = False
        self._generation = self._sampler.set_active(False)
        self._visibility.stop()
        if self._watched_window is not None:
            try:
                self._watched_window.removeEventFilter(self)
            except RuntimeError:
                pass
            self._watched_window = None
        super().hideEvent(event)

    def _sync_visibility(self):
        self._sampling = (self.toggle.isChecked() and self.details is not None
                          and self.isVisible() and not self.window().isMinimized()
                          and not self.details.visibleRegion().isEmpty())
        self._generation = self._sampler.set_active(self._sampling)

    @Slot(int, object)
    def _on_sample(self, generation, _notification):
        if not self._sampling or generation != self._generation:
            return
        sample = self._sampler.take(generation)
        if sample is None:
            return
        main, private, child, seconds = sample
        numbers = [f'{value / 1048576:.1f} MB' if value is not None else '—'
                   for value in (main, child, private)]
        if seconds is None:
            numbers.append('—')
        else:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            numbers.append(f'{hours:02}:{minutes:02}:{seconds:02}')
        for widget, text in zip(self.values, numbers):
            if widget.text() != text:
                widget.setText(text)
