"""Live pronunciation search. Isolated TSF text host preserves Korean input focus."""
import ctypes
import json
from pathlib import Path
import sys
from PySide6.QtCore import QEvent, QObject, QProcess, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout


class PronunciationEdit(QLineEdit):
    searched = Signal(str)

    def __init__(self):
        super().__init__()
        self.preedit = ''
        self.textChanged.connect(lambda _: self.searched.emit(self.effective_text()))

    def effective_text(self):
        position = self.cursorPosition()
        return self.text()[:position] + self.preedit + self.text()[position:]

    def inputMethodEvent(self, event):
        self.preedit = event.preeditString()
        super().inputMethodEvent(event)
        self.searched.emit(self.effective_text())


class CandidatePanel(QObject):
    def __init__(self):
        super().__init__()
        self.window = None
        self.process = None
        self.target = 0
        self.query = self.wanted = self.displayed = ''
        self.revision = 0

    @property
    def enabled(self):
        return self.window is not None and self.window.isVisible()

    def _build(self):
        self.window = QDialog()
        self.window.setWindowTitle('Lexift · 한–일 변환')
        self.window.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.window.resize(560, 470)
        self.window.setMinimumSize(420, 320)
        self.window.setStyleSheet('''
            QDialog { background:#f5f7fb; color:#172238; font-family:"Malgun Gothic"; }
            QLabel { color:#66748a; font-size:12px; }
            QLabel#title { color:#172238; font-size:20px; font-weight:600; }
            QLineEdit { background:white; color:#172238; border:2px solid #ccd7e8;
                border-radius:12px; padding:13px 16px; font-size:20px; selection-background-color:#dbe8ff; }
            QLineEdit:focus { border-color:#608fe9; }
            QListWidget { background:white; color:#172238; border:1px solid #e1e7f0;
                border-radius:12px; padding:6px; font-family:"Yu Gothic UI"; font-size:21px; outline:0; }
            QListWidget::item { padding:10px 12px; border-radius:8px; }
            QListWidget::item:selected { background:#e8efff; color:#214fba; }
            QPushButton { background:#e8efff; color:#214fba; border:0; border-radius:7px; padding:6px 12px; }
        ''')
        layout = QVBoxLayout(self.window)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel('한–일 변환'); title.setObjectName('title')
        header.addWidget(title); header.addStretch(); header.addWidget(QLabel('Lexift'))
        layout.addLayout(header)
        self.search = PronunciationEdit()
        self.search.setPlaceholderText('한글 발음 검색 · 예: 와타시')
        self.search.setMaxLength(256)
        layout.addWidget(self.search)
        self.reading = QLabel('한글 발음을 입력하면 일본어 후보가 나타납니다.')
        self.reading.setWordWrap(True)
        layout.addWidget(self.reading)
        self.candidates = QListWidget()
        self.candidates.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.candidates, 1)
        footer = QHBoxLayout()
        self.status = QLabel('↑ ↓ 선택   ·   Enter 입력   ·   Esc 닫기')
        footer.addWidget(self.status, 1)
        copy = QPushButton('복사'); copy.clicked.connect(self.copy_selected)
        footer.addWidget(copy); layout.addLayout(footer)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True); self.debounce.setInterval(180)
        self.debounce.timeout.connect(self._start_query)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True); self.timeout.setInterval(5000)
        self.timeout.timeout.connect(self._timed_out)
        self.search.searched.connect(self._changed)
        self.search.installEventFilter(self)
        self.window.installEventFilter(self)
        self.candidates.itemClicked.connect(lambda _: self.commit())

    def open(self, target=0):
        if self.window is None:
            self._build()
        self.target = int(target or 0)
        self.window.show(); self.window.raise_(); self.window.activateWindow()
        self.search.setFocus(); self.search.selectAll()
        from ime_windows import user32, WM_INPUTLANGCHANGEREQUEST
        user32.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        user32.GetKeyboardLayoutList.restype = ctypes.c_int
        layouts = (ctypes.c_void_p * 64)()
        count = user32.GetKeyboardLayoutList(64, layouts)
        for hkl in layouts[:count]:
            if hkl and hkl & 0xffff == 0x0412:
                user32.PostMessageW(int(self.search.winId()), WM_INPUTLANGCHANGEREQUEST, 0, hkl)
                break
        if self.search.effective_text():
            self._changed(self.search.effective_text())

    def toggle(self, target=0):
        if self.enabled:
            self.window.hide()
        else:
            self.open(target)
        return self.enabled

    def close(self):
        if self.window:
            self.window.hide()
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill(); self.process.waitForFinished(1000)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Type.Hide:
            self.debounce.stop()
        if obj is self.search and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                count = self.candidates.count()
                if count:
                    delta = 1 if event.key() == Qt.Key.Key_Down else -1
                    self.candidates.setCurrentRow((self.candidates.currentRow() + delta) % count)
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.commit(); return True
        return super().eventFilter(obj, event)

    def _changed(self, text):
        self.revision += 1
        self.wanted = text; self.displayed = ''
        self.candidates.clear(); self.debounce.stop()
        self.reading.setText('검색 중…' if text.strip() else '한글 발음을 입력하면 일본어 후보가 나타납니다.')
        if text.strip():
            self.debounce.start()

    def _start_query(self):
        if not self.enabled or not self.wanted.strip():
            return
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            return
        folder = Path(__file__).resolve().parent
        host = (folder if getattr(sys, 'frozen', False) else folder.parent) / 'lab' / 'ime_candidate_host.exe'
        if not host.is_file():
            self.reading.setText('IME 후보 추출 파일이 없습니다. Lexift를 다시 설치해 주세요.'); return
        self.query = self.wanted; self.query_revision = self.revision
        process = self.process = QProcess(self)
        process.setProgram(str(host)); process.setArguments(['--query-live', self.query])
        process.finished.connect(lambda code, status: self._finished(process, code))
        process.errorOccurred.connect(lambda error: self._process_error(process, error))
        process.start(); self.timeout.start()

    def _process_error(self, process, error):
        if process is self.process and error == QProcess.ProcessError.FailedToStart:
            self.timeout.stop(); self.reading.setText('일본어 IME 검색을 시작하지 못했습니다.')

    def _timed_out(self):
        if self.process:
            self.process.kill()
        self.reading.setText('IME 응답이 지연되었습니다. 다시 입력해 주세요.')

    def _finished(self, process, code):
        if process is not self.process:
            process.deleteLater(); return
        self.timeout.stop()
        current = self.query_revision == self.revision
        if current and self.enabled:
            try:
                result = json.loads(bytes(process.readAllStandardOutput()).decode('utf-8'))
                if code != 0 or result.get('error'):
                    raise ValueError(result.get('error') or '일본어 IME가 응답하지 않았습니다.')
                self.reading.setText(result['kana'])
                values = [v for v in result['candidates'] if v and v not in ('単漢字...', '単漢字…')]
                self.candidates.addItems(values)
                if values:
                    self.displayed = self.query; self.candidates.setCurrentRow(0)
                else:
                    self.reading.setText(result['kana'] + ' · 후보가 없습니다.')
            except (ValueError, KeyError, UnicodeError):
                self.reading.setText('일본어 IME 후보를 불러오지 못했습니다. 발음을 확인해 주세요.')
        self.process = None; process.deleteLater()
        if not current and self.enabled:
            self._start_query()

    def _selection(self):
        if self.displayed != self.search.effective_text():
            return ''
        item = self.candidates.currentItem()
        return item.text() if item else ''

    def copy_selected(self):
        text = self._selection()
        if text:
            QApplication.clipboard().setText(text)
            self.status.setText('복사했습니다 · ' + text); self.search.setFocus()

    def commit(self):
        text = self._selection()
        if not text:
            return
        from ime_windows import user32
        if not self.target or not user32.IsWindow(self.target):
            self.copy_selected(); return
        target = self.target
        self.window.hide(); user32.SetForegroundWindow(target)
        QTimer.singleShot(80, lambda: self._insert(target, text))

    def _insert(self, target, text):
        from ime_windows import target_is_foreground, user32, INPUT, INPUT_UNION, KEYBDINPUT, INPUT_KEYBOARD, KEYEVENTF_KEYUP
        if not target_is_foreground(target):
            QApplication.clipboard().setText(text); return
        events = []
        encoded = text.encode('utf-16-le')
        for i in range(0, len(encoded), 2):
            unit = int.from_bytes(encoded[i:i+2], 'little')
            for flags in (0x0004, 0x0004 | KEYEVENTF_KEYUP):
                events.append(INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(0, unit, flags, 0, 0))))
        array = (INPUT * len(events))(*events)
        if user32.SendInput(len(events), array, ctypes.sizeof(INPUT)) != len(events):
            QApplication.clipboard().setText(text)


_panel = None


def candidate_panel():
    global _panel
    if _panel is None:
        _panel = CandidatePanel()
    return _panel
