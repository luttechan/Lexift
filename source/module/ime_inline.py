"""Korean pronunciation candidates at the caret in the foreground application."""
import json
from pathlib import Path
import sys
import os
if sys.platform=='win32':
    os.environ.setdefault('QT_QPA_PLATFORM','windows:fontengine=gdi')
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QObject, QPoint, QProcess, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QListWidget, QVBoxLayout
from i18n import tr


def host_path():
    folder = Path(__file__).resolve().parent
    return (folder if getattr(sys, 'frozen', False) else folder.parent)/'lab'/'ime_candidate_host.exe'


def caret_point(snapshot):
    """Map physical UIA coordinates using the caret's monitor, including its origin."""
    from ime_windows import user32,MonitorInfo,screen_for_monitor
    user32.MonitorFromPoint.argtypes=[wintypes.POINT,wintypes.DWORD]
    user32.MonitorFromPoint.restype=ctypes.c_void_p
    user32.GetMonitorInfoW.argtypes=[ctypes.c_void_p,ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype=wintypes.BOOL
    x,y=snapshot['x'],snapshot['y']
    monitor=user32.MonitorFromPoint(wintypes.POINT(x,y),2)
    info=MonitorInfo();info.size=ctypes.sizeof(info)
    screen=QApplication.primaryScreen()
    if monitor and user32.GetMonitorInfoW(monitor,ctypes.byref(info)):
        screen=screen_for_monitor(info,QApplication.screens(),screen)
        origin=screen.geometry().topLeft();ratio=screen.devicePixelRatio()
        return QPoint(origin.x()+round((x-info.monitor.left)/ratio),origin.y()+round((y-info.monitor.top)/ratio)+6),screen
    ratio=screen.devicePixelRatio()
    return QPoint(round(x/ratio),round(y/ratio)+6),screen


def popup_coordinates(point,bounds,width,height,caret_height=20):
    """Keep the popup next to the caret and entirely within its monitor."""
    x=max(bounds.left(),min(point.x(),bounds.right()-width+1))
    y=point.y()
    if y+height>bounds.bottom()+1:
        y=point.y()-height-max(1,caret_height)-12
    y=max(bounds.top(),min(y,bounds.bottom()-height+1))
    return x,y


class CandidateFrame(QFrame):
    painted=Signal()

    def paintEvent(self, event):
        super().paintEvent(event)
        self.painted.emit()


class InlineMode(QObject):
    visibility_changed = Signal(bool)
    failed = Signal(str)
    presented = Signal(str)

    def __init__(self):
        super().__init__()
        self.enabled = False
        self.language = 'ja'
        self.paused = False
        self.watcher = None
        self.idle_release=QTimer(self);self.idle_release.setSingleShot(True)
        self.idle_release.setInterval(3000);self.idle_release.timeout.connect(self._release_idle)
        self.query = None
        self.engines = {}
        self.dictionary=None
        self._paint_source = None
        self._shown_identity = None
        self._user_selected=False;self._updating_list=False
        self.snapshot = {}
        self.buffer = b''
        self.caches = {name:{} for name in ('ja','zh','zh_tw','zh_bopomofo')}
        self.cache = self.caches['ja']
        self.dismissed = None
        self.last_replace = None
        self.last_query = None
        self.pending_commit = None
        self._committed_identity = None
        self.commit_timer=QTimer(self);self.commit_timer.setSingleShot(True);self.commit_timer.setInterval(2500)
        self.commit_timer.timeout.connect(self._commit_timeout)
        self.overlay = None
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True); self.debounce.setInterval(0)
        self.debounce.setTimerType(Qt.TimerType.PreciseTimer)
        self.debounce.timeout.connect(self._search)
        self.focus_guard=QTimer(self);self.focus_guard.setInterval(30)
        self.focus_guard.timeout.connect(self._check_focus)
        self.watcher_retry=QTimer(self);self.watcher_retry.setSingleShot(True)
        self.watcher_retry.timeout.connect(self._start_watcher)
        self.query_retry=QTimer(self);self.query_retry.setSingleShot(True)
        self.query_retry.timeout.connect(self._restore_query)
        self.watcher_health=QTimer(self);self.watcher_health.setSingleShot(True)
        self.watcher_health.setInterval(8000);self.watcher_health.timeout.connect(self._watcher_unresponsive)
        self._watcher_attempts=0;self._query_attempts=0;self._reported_errors=set()

    def _build(self):
        self.overlay = CandidateFrame()
        self.overlay.painted.connect(self._painted)
        self.overlay.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.overlay.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.overlay.setObjectName('inline')
        self.overlay.setStyleSheet('''
            QFrame#inline { background:#ffffff; border:1px solid #dce4f0; border-radius:12px; }
            QLabel { color:#64738a; background:transparent; border:0; font-size:12px; }
            QLabel#reading { color:#254a82; font-size:14px; }
            QListWidget { background:transparent; color:#172238; border:0; outline:0;
                font-size:20px; }
            QListWidget::item { padding:7px 10px; border-radius:7px; }
            QListWidget::item:selected { background:#e8efff; color:#214fba; }
        ''')
        body=QVBoxLayout(self.overlay); body.setContentsMargins(12,10,12,10); body.setSpacing(6)
        from candidate_delegate import ReadingLabel
        self.reading=ReadingLabel(); self.reading.setObjectName('reading'); body.addWidget(self.reading)
        self.list=QListWidget(); self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        from candidate_delegate import CandidateDelegate
        self.list.setItemDelegate(CandidateDelegate(self.list))
        self.list.setUniformItemSizes(True)
        self.list.currentRowChanged.connect(self._selected_row_changed)
        body.addWidget(self.list)
        self.hint=QLabel(tr('1–9 / 0 확정 / ↑↓ 이동 / Space / Enter'));body.addWidget(self.hint)
        self.list.itemClicked.connect(lambda _:self.commit())

    def _selected_row_changed(self,row):
        if not self._updating_list and self._shown_identity is not None:
            self._user_selected=True
            readings=getattr(self,'_candidate_readings',[])
            if 0<=row<len(readings):
                self.reading.setText(self.snapshot['source']+'  →  '+readings[row])

    def _commit_timeout(self):
        self._engine_failed('입력 연결을 다시 시도합니다.')

    def _painted(self):
        if self._paint_source is not None:
            source=self._paint_source;self._paint_source=None
            self.presented.emit(source)

    def prepare(self, language=None):
        if self.overlay is None:
            self._build()
            self.overlay.winId()  # create the non-activating native tool window while hidden
        languages=(('zh' if language in ('zh_tw','zh_bopomofo') else language),) if language else ('ja','zh')
        for name in languages:
            if name in self.engines:
                continue
            if name=='zh':
                from chinese_query_client import ChineseQueryClient
                client=ChineseQueryClient(self)
            else:
                from ime_query_client import QueryClient
                client=QueryClient(host_path(),self)
            self.engines[name]=client
            client.result.connect(lambda serial,data,client=client:self._queried(client,data))
            client.failed.connect(lambda message,client=client,name=name:self._client_failed(name,client,message))
            client.start()
            if name=='ja':
                # Load the IME's conversion data with a fixed public reading;
                # this never watches an input field or displays a candidate.
                client.request('와타시')

    def _client_failed(self, name, client, message):
        if self.engines.get(name) is not client:return
        self.engines.pop(name,None)
        client.stop()
        if client is self.query:
            self.query=None
            if self.enabled:
                self._report_recovery(message)
                self._query_attempts+=1
                self.query_retry.start(min(30000,500*2**min(self._query_attempts,6)))

    def _restore_query(self):
        if not self.enabled:return
        self.prepare(self.language)
        self.query=self.engines.get('ja' if self.language=='ja' else 'zh')
        self._search()

    def _report_recovery(self,message):
        if message not in self._reported_errors:
            self._reported_errors.add(message);self.failed.emit(message)

    def _start_watcher(self):
        if not self.enabled or self.watcher:return
        process=self.watcher=QProcess(self);self.buffer=b''
        process.setProgram(str(host_path()));process.setArguments(['--watch-input','--owner-pid',str(os.getpid())])
        process.readyReadStandardOutput.connect(lambda:self._read(process))
        process.finished.connect(lambda:self._watcher_stopped(process))
        process.errorOccurred.connect(lambda error:self._watcher_error(process,error))
        process.started.connect(lambda:self._watcher_started(process))
        process.start();self.watcher_health.start()

    def _watcher_started(self,process):
        if process is self.watcher and self.paused:process.write(b'PAUSE 1\n')

    def _watcher_unresponsive(self):
        self._engine_failed('입력 연결을 다시 시도합니다.')

    def shutdown(self):
        self.close()
        for client in tuple(self.engines.values()):
            client.stop()
        self.engines.clear()
        for cache in self.caches.values():cache.clear()

    def release(self,language):
        if language=='zh_tw':
            if self.enabled and self.language in ('zh_tw','zh_bopomofo'):self.close()
            self.caches['zh_tw'].clear();self.caches['zh_bopomofo'].clear()
            return
        if self.enabled and self.language==language:self.close()
        if language=='zh' and self.enabled and self.language in ('zh_tw','zh_bopomofo'):
            self.caches['zh'].clear();return
        client=self.engines.pop(language,None)
        if client:client.stop()
        self.caches[language].clear()

    def _release_idle(self):
        if not self.enabled:
            for client in tuple(self.engines.values()):client.stop()
            self.engines.clear()
            for cache in self.caches.values():cache.clear()

    def toggle(self, language='ja'):
        self.idle_release.stop()
        if language not in ('ja','zh','zh_tw','zh_bopomofo'):
            raise ValueError('Unsupported conversion language')
        if self.enabled and self.language != language:
            self.close()
        if self.enabled:
            self.close()
        else:
            self.language=language
            self.cache=self.caches[language]
            if not host_path().is_file():
                raise RuntimeError('일본어 IME 후보 추출 파일이 없습니다.')
            if self.overlay is None:
                self._build()
            self.enabled=True; self.snapshot={}; self.buffer=b''; self.dismissed=None
            self._reported_errors.clear();self._watcher_attempts=0;self._query_attempts=0
            self.focus_guard.start()
            self._start_watcher()
            self.prepare(language)
            self.query=self.engines.get('ja' if language=='ja' else 'zh')
            if self.query is None:self.query_retry.start(1000)
        return self.enabled

    def visible(self):
        return self.overlay is not None and self.overlay.isVisible()

    def _hide(self):
        self._paint_source=None
        self._shown_identity=None
        self._user_selected=False
        if self.visible():
            self.overlay.hide(); self.visibility_changed.emit(False)

    def set_paused(self, paused):
        self.paused=bool(paused)
        if self.watcher:self.watcher.write(b'PAUSE 1\n' if self.paused else b'PAUSE 0\n')
        if paused:
            self.debounce.stop()
            if self.query:self.query.cancel()
            self._hide()
        elif self.enabled:
            self.debounce.start()

    def close(self):
        self.watcher_retry.stop();self.query_retry.stop();self.watcher_health.stop()
        self.idle_release.start()
        guarded=self.pending_commit is not None
        self.pending_commit=None;self._committed_identity=None;self.commit_timer.stop()
        self.focus_guard.stop()
        self.enabled=False; self.debounce.stop(); self._hide(); self.snapshot={}
        if guarded:self.visibility_changed.emit(False)
        self.last_query=None; self.last_replace=None
        if self.query:
            client=self.query;self.query=None
            if client in self.engines.values():
                client.cancel()
            else:
                client.stop()
        if self.watcher:
            self.watcher.write(b'QUIT\n')
            process=self.watcher
            self.watcher=None
            QTimer.singleShot(600,lambda:self._kill_watcher(process))

    def _kill_watcher(self, process):
        try:
            if process.state()!=QProcess.ProcessState.NotRunning:
                process.kill()
        except RuntimeError:
            pass

    def _watcher_stopped(self, process):
        if process is self.watcher:
            self.watcher=None
            self._engine_failed('입력 감지 엔진이 종료되었습니다.')
        try:
            process.deleteLater()
        except RuntimeError:
            pass  # Qt can finish a child QProcess during parent destruction.

    def _watcher_error(self, process, error):
        if process is self.watcher and error==QProcess.ProcessError.FailedToStart:
            self._engine_failed('입력 감지 엔진을 시작하지 못했습니다.')
            process.deleteLater()

    def _engine_failed(self, message):
        if self.enabled:
            # Preserve ON, discard stale work and never replay a commit.
            self.commit_timer.stop();self.pending_commit=None;self._committed_identity=None
            self.snapshot={};self.dismissed=None;self.debounce.stop();self._hide()
            self.visibility_changed.emit(False);self.watcher_health.stop()
            process=self.watcher;self.watcher=None
            if process:process.kill()
            self._report_recovery(message)
            self._watcher_attempts+=1
            self.watcher_retry.start(min(30000,250*2**min(self._watcher_attempts,7)))

    def _check_focus(self):
        if self.visible():
            from ime_windows import user32
            if user32.GetForegroundWindow()!=self.snapshot.get('hwnd'):
                self._hide()

    def _read(self, process):
        if process is not self.watcher:
            return
        self.buffer+=bytes(process.readAllStandardOutput())
        self.watcher_health.start()
        latest=None
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:
                data=json.loads(line.decode('utf-8'))
            except (ValueError,UnicodeError):
                continue
            if data.get('event')=='heartbeat':continue
            if data.get('event')=='input':
                if data.get('source'):self._watcher_attempts=0
                latest=data
            elif data.get('event')=='replace':
                if not self.pending_commit or data.get('serial')!=self.pending_commit['serial']:
                    continue
                latest=None
                self.last_replace=data
                if self.pending_commit and data.get('serial')==self.pending_commit['serial']:
                    self.pending_commit=None;self.commit_timer.stop()
                    if not data.get('success'):
                        self._committed_identity=None;self.dismissed=None
                    self.visibility_changed.emit(False)
                self._hide()
        if latest is not None:
            identity=(latest.get('hwnd'),latest.get('source'))
            if identity!=self._committed_identity:self._committed_identity=None
            self.snapshot=latest; self.debounce.stop()
            if self.pending_commit or identity==self._committed_identity:
                return
            self.dismissed=None
            if self.enabled and latest.get('source') and not self.paused:
                text=latest['source']
                if text in self.cache:
                    self._show(self.cache[text])
                else:
                    if self.dictionary and self.dictionary.lookup(self.language,text):
                        self._show({'kana':latest.get('kana',text),'candidates':[],'preview':True})
                    elif self.language=='ja' and latest.get('kana'):
                        self._show({'kana':latest['kana'],'candidates':latest.get('kana_variants') or [latest['kana']],
                                    'preview':True})
                    else:self._hide()
                    self.debounce.start()
            else:self._hide()

    def _search(self):
        text=self.snapshot.get('source','')
        if not self.enabled or self.paused or self.pending_commit or not text or self.dismissed==self.snapshot.get('serial'):
            return
        if text in self.cache:
            self._show(self.cache[text]); return
        if self.query:
            if self.language=='ja':self.query.request(text)
            else:self.query.request(text,self.language)

    def _queried(self, client, data):
        if client is not self.query or not self.enabled:
            return
        if self.language!='ja' and data.get('output_mode','zh')!=self.language:return
        self._query_attempts=0
        self.last_query={'data':data}
        text=data.get('source','')
        if self.language=='ja' and data.get('candidates'):
            values=list(dict.fromkeys(data['candidates']+data.get('kana_variants',[])))
            by_value=dict(zip(data['candidates'],data.get('readings',[])))
            variants=data.get('kana_variants',[])
            data=dict(data,candidates=values,readings=[by_value.get(v,v if v in variants else data['kana']) for v in values])
        if data.get('candidates') or (self.dictionary and self.dictionary.lookup(self.language,text)):
            if not data.get('partial'):
                if len(self.cache)>=32:
                    self.cache.pop(next(iter(self.cache)))
                self.cache[text]=data
            if text==self.snapshot.get('source'):
                self._show(data)

    def _show(self, data):
        from ime_windows import user32
        if self.dictionary:
            data=self.dictionary.merge(self.language,self.snapshot.get('source',''),data)
        if not self.enabled or self.paused or self.pending_commit or self.dismissed==self.snapshot.get('serial'):
            return
        if (self.snapshot.get('hwnd'),self.snapshot.get('source'))==self._committed_identity:return
        if user32.GetForegroundWindow()!=self.snapshot.get('hwnd'):
            return
        indices=[n for n,v in enumerate(data['candidates']) if v and v not in ('単漢字...', '単漢字…')]
        values=[data['candidates'][n] for n in indices]
        if not values:
            return
        identity=(self.snapshot.get('hwnd'),self.snapshot['source'])
        was_visible=self.visible();previous_identity=self._shown_identity
        current=self.list.currentItem()
        selected=current.text() if self.visible() and self._shown_identity==identity and self._user_selected and current else None
        if self._shown_identity!=identity:self._user_selected=False
        if selected is not None and selected not in values:
            selected=None;self._user_selected=False
        scroll=self.list.verticalScrollBar().value()
        unchanged=self.list.count()==len(values) and all(self.list.item(n).text()==v for n,v in enumerate(values))
        self._updating_list=True
        if not unchanged:
            self.list.setUpdatesEnabled(False)
            self.list.clear();self.list.addItems(values)
        row=values.index(selected) if selected in values else 0
        self.list.setCurrentRow(row)
        self._updating_list=False
        self._shown_identity=identity
        readings=data.get('readings',[])
        alternatives=data.get('reading_alternatives',{})
        self._candidate_readings=[' / '.join(alternatives.get(data['candidates'][n],[])) or
                                  (readings[n] if n<len(readings) else data['kana']) for n in indices]
        self._reading_default=data['kana']
        self.hint.setText(tr('Lexift / 한자 후보 준비 중…') if data.get('preview') and not data.get('custom') else tr('1–9 / 0 확정 / ↑↓ 이동 / Space / Enter'))
        row=self.list.currentRow()
        selected_reading=self._candidate_readings[row] if row<len(self._candidate_readings) else data['kana']
        self.reading.setText(self.snapshot['source']+'  →  '+selected_reading)
        point,screen=caret_point(self.snapshot)
        bounds=screen.availableGeometry()
        self.overlay.resize(min(330,bounds.width()),min(min(6,len(values))*42+78,bounds.height()))
        # Qt can scroll to row zero before the hidden view receives its new
        # viewport size. Restore only a deliberate selection; new input starts
        # with candidate 1 at the top after the final layout has settled.
        if selected is None:
            self.list.scrollToTop()
        elif unchanged:
            self.list.verticalScrollBar().setValue(scroll)
        else:
            self.list.scrollToItem(self.list.item(row))
        self.list.setUpdatesEnabled(True)
        caret_height=round(self.snapshot.get('caret_height',20)/screen.devicePixelRatio())
        x,y=popup_coordinates(point,bounds,self.overlay.width(),self.overlay.height(),caret_height)
        self.overlay.move(x,y);self._paint_source=self.snapshot['source']
        self.overlay.show()
        if not was_visible:self.overlay.raise_()
        self.overlay.update()
        if selected is None:
            if not unchanged or not was_visible or previous_identity!=identity:self.list.doItemsLayout()
            self.list.scrollToTop()
        if not was_visible or not previous_identity or previous_identity[0]!=identity[0]:
            self.visibility_changed.emit(True)

    def navigate(self, key):
        if not self.visible():
            return
        from ime_windows import user32
        if user32.GetForegroundWindow()!=self.snapshot.get('hwnd'):
            self._hide();return
        if key==0x1b:
            self.dismissed=self.snapshot.get('serial'); self._hide()
        elif key in (0x0d,0x20):
            self.commit()
        elif 0x30<=key<=0x39 or 0x60<=key<=0x69:
            digit=key-(0x60 if key>=0x60 else 0x30)
            row=(digit or 10)-1
            if row<self.list.count():
                self.list.setCurrentRow(row)
                self.commit()
        elif key in (0x26,0x28):
            self.list.setCurrentRow((self.list.currentRow()+(-1 if key==0x26 else 1))%self.list.count())

    def commit(self):
        from ime_windows import user32
        item=self.list.currentItem()
        if not self.enabled or self.pending_commit or not item or not self.watcher:
            return
        if user32.GetForegroundWindow()!=self.snapshot.get('hwnd'):
            self._hide(); return
        text=item.text()
        units=text.encode('utf-16-le')
        encoded=''.join(f'{int.from_bytes(units[i:i+2],"little"):04x}' for i in range(0,len(units),2))
        self.pending_commit=dict(self.snapshot)
        self._committed_identity=(self.snapshot.get('hwnd'),self.snapshot.get('source'))
        self.commit_timer.start();self.debounce.stop()
        if self.query:self.query.cancel()
        # The controller keeps Space guarded until the native replace reply.
        self.visibility_changed.emit(False)
        self.watcher.write(f'REPLACE {self.snapshot["serial"]} {encoded}\n'.encode('ascii'))
        self.dismissed=self.snapshot.get('serial'); self._hide()


_inline=None


def inline_mode():
    global _inline
    if _inline is None:
        _inline=InlineMode()
    return _inline
