"""Persistent IME engine with latest-request wins and bounded shutdown."""
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
import json


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
        self.process.errorOccurred.connect(self._error)
        self.process.finished.connect(self._finished)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(15000)
        self.timer.timeout.connect(lambda:self._fail('일본어 IME 응답 시간이 초과되었습니다.'))
        self.buffer=b'';self.ready=False;self.closed=False;self.serial=0;self.pending=None

    def start(self):
        self.process.start();self.timer.start()

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
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:
                data=json.loads(line.decode('utf-8'))
            except (ValueError,UnicodeError):
                self._fail('일본어 IME 응답을 읽지 못했습니다.');return
            if self.closed:
                continue
            if data.get('event')=='ready':
                self.ready=True;self.timer.stop();self._send()
            elif data.get('id')==self.serial:
                if data.get('partial'):
                    self.timer.start()
                else:
                    self.timer.stop()
                    self.pending=None
                self.result.emit(self.serial,data)

    def _error(self, error):
        if error==QProcess.ProcessError.FailedToStart:
            self._fail('일본어 IME 엔진을 시작하지 못했습니다.')

    def _finished(self, *_):
        if not self.closed:
            self._fail('일본어 IME 엔진이 종료되었습니다.')
        self.deleteLater()

    def _fail(self, message):
        if self.closed:
            return
        self.stop();self.failed.emit(message)

    def stop(self):
        if self.closed:
            return
        self.closed=True;self.ready=False;self.timer.stop();self.pending=None
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
