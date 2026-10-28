"""Persistent IME engine with latest-request wins and bounded shutdown."""
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
import json
import logging


def encode_text(text):
    data=text.encode('utf-16-le')
    return ''.join(f'{int.from_bytes(data[i:i+2],"little"):04x}' for i in range(0,len(data),2))


class QueryClient(QObject):
    result=Signal(int,dict)
    failed=Signal(str)

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.process=QProcess(self)
        self.process.setProgram(str(host));self.process.setArguments(['--query-server'])
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.readyReadStandardError.connect(self._stderr)
        self.process.errorOccurred.connect(self._error)
        self.process.finished.connect(self._finished)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(15000)
        self.timer.timeout.connect(self._timeout)
        self.restart_timer=QTimer(self);self.restart_timer.setSingleShot(True)
        self.restart_timer.timeout.connect(self._restart)
        self.buffer=b'';self.ready=False;self.closed=False;self.serial=0;self.pending=None
        self.trace=b'';self.recoveries=0;self.shared_desktop=False
        self.retry_private=False

    def start(self):
        if self.closed:return
        self.shared_desktop='--shared-desktop' in self.process.arguments()
        self.process.start();self.timer.start()

    def _restart(self):
        if not self.closed:self.start()

    def _stderr(self):
        # Native stages contain no text from the user's document. Keep a small
        # tail in memory and write it to the rotating app log only on failure.
        self.trace=(self.trace+bytes(self.process.readAllStandardError()))[-4096:]

    def _timeout(self):
        if self.closed:return
        logging.warning('Japanese query timeout; ready=%s; stages=%s',self.ready,self.trace.decode('utf-8',errors='replace'))
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.kill()  # finished handles bounded recovery
        else:self._fail('일본어 IME 응답 시간이 초과되었습니다.')

    def request(self, text):
        if self.closed or not text:
            return
        if self.pending and self.pending[1]==text:
            return self.pending[0]
        self.serial+=1;self.pending=(self.serial,text)
        self._send()
        return self.serial

    def cancel(self):
        self.serial+=1;self.pending=None
        if self.ready:
            self.timer.stop()
            self.process.write(b'CANCEL\n')

    def _send(self):
        if self.ready and self.pending and not self.closed:
            serial,text=self.pending
            self.process.write(f'QUERY {serial} {encode_text(text)}\n'.encode('ascii'))
            self.timer.start()

    def _read(self):
        self.buffer+=bytes(self.process.readAllStandardOutput())
        if len(self.buffer)>16*1024*1024:
            self.buffer=b'';self._fail('일본어 IME 응답을 읽지 못했습니다.');return
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:
                data=json.loads(line.decode('utf-8'))
            except (ValueError,UnicodeError):
                self._fail('일본어 IME 응답을 읽지 못했습니다.');return
            if not isinstance(data,dict):
                self._fail('일본어 IME 응답을 읽지 못했습니다.');return
            candidates=data.get('candidates',[])
            if (not isinstance(candidates,list) or len(candidates)>220 or
                    any(not isinstance(value,str) or len(value)>8192 or '\x00' in value for value in candidates) or
                    any(not isinstance(data.get(key,''),str) or len(data.get(key,''))>8192 for key in ('source','kana'))):
                self._fail('일본어 IME 응답을 읽지 못했습니다.');return
            if self.closed:
                continue
            if data.get('event')=='ready':
                self.ready=True;self.timer.stop();self._send()
            elif data.get('id')==self.serial:
                if not data.get('partial') and not candidates and not data.get('error'):
                    if self.shared_desktop and self.recoveries<2:
                        self.retry_private=True;self.process.kill();return
                    self._fail('일본어 IME 후보를 가져오지 못했습니다.');return
                if data.get('partial'):
                    self.timer.start()
                else:
                    self.timer.stop()
                    self.pending=None
                    self.recoveries=0
                self.result.emit(self.serial,data)

    def _error(self, error):
        if error==QProcess.ProcessError.FailedToStart:
            logging.warning('Japanese query failed to start: %s; program=%s',self.process.errorString(),self.process.program())
            self._fail('일본어 IME 엔진을 시작하지 못했습니다.')

    def _finished(self, code=0, status=None):
        if self.closed:
            self.deleteLater();return
        self._stderr()
        was_ready=self.ready;self.ready=False;self.timer.stop();self.buffer=b''
        logging.warning('Japanese query exited; code=0x%08X; ready=%s; shared_desktop=%s; stages=%s',
                        code & 0xffffffff,was_ready,self.shared_desktop,self.trace.decode('utf-8',errors='replace'))
        # The private desktop can have a different loaded-profile cache. A
        # missing profile there must be checked once on the shared desktop.
        if (code!=3 or (not was_ready and not self.shared_desktop)) and self.recoveries<2:
            self.recoveries+=1
            # Some Windows sessions disallow another desktop or cannot start
            # TSF there. A hidden window on this desktop is the fallback. It
            # never activates a foreground window or sends keyboard input.
            if self.retry_private:
                self.retry_private=False;self.shared_desktop=False
                self.process.setArguments(['--query-server'])
            elif not was_ready and not self.shared_desktop:
                self.shared_desktop=True
                self.process.setArguments(['--query-server','--shared-desktop'])
            self.trace=b''
            self.restart_timer.start(150*self.recoveries)
            return
        message=('일본어 IME 프로필을 사용할 수 없습니다.' if code==3 else
                 '일본어 변환 엔진을 다시 연결하지 못했습니다.')
        self._fail(f'{message} (0x{code & 0xffffffff:08X})')

    def _fail(self, message):
        if self.closed:
            return
        self.stop();self.failed.emit(message)

    def stop(self):
        if self.closed:
            return
        self.closed=True;self.ready=False;self.timer.stop();self.restart_timer.stop();self.pending=None
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.write(b'QUIT\n')
            QTimer.singleShot(600,self._kill)
        else:
            self.deleteLater()

    def _kill(self):
        try:
            if self.process.state()!=QProcess.ProcessState.NotRunning:
                self.process.kill()
        except RuntimeError:
            pass
