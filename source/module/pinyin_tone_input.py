"""One-shot native replacement: no keystroke history, clipboard, or permanent watcher."""
import json,os
from PySide6.QtCore import QObject,QProcess,QTimer,Signal
from ime_inline import host_path
from ime_query_client import encode_text
from pinyin_tones import apply_tone

class ToneInput(QObject):
    failed=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.process=None;self.buffer=b'';self.target=0;self.tone=0;self.sent=False
        self.timeout=QTimer(self);self.timeout.setSingleShot(True);self.timeout.setInterval(1800)
        self.timeout.timeout.connect(self.cancel)

    def apply(self,hwnd,tone):
        from ime_windows import target_is_foreground
        if not hwnd or not target_is_foreground(hwnd):return
        self.cancel();self.target=hwnd;self.tone=tone;self.sent=False;self.buffer=b''
        process=self.process=QProcess(self)
        process.setProgram(str(host_path()));process.setArguments(['--watch-roman','--owner-pid',str(os.getpid())])
        process.readyReadStandardOutput.connect(lambda:self._read(process))
        process.finished.connect(lambda:self._finished(process))
        process.errorOccurred.connect(lambda _:self._finished(process))
        process.start();self.timeout.start()

    def _read(self,process):
        if process is not self.process:return
        self.buffer+=bytes(process.readAllStandardOutput())
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:data=json.loads(line)
            except ValueError:continue
            if data.get('event')=='replace':self.cancel();return
            if data.get('event')!='input' or self.sent:continue
            # Hotkeys capture the focused child; native snapshots identify its
            # top-level owner. Also recheck the exact child to reject focus races.
            from ime_windows import _root,target_is_foreground
            if data.get('hwnd')!=_root(self.target) or not target_is_foreground(self.target):
                self.cancel();return
            source=data.get('source','');replacement=apply_tone(source,self.tone)
            if source and replacement!=source:
                self.sent=True;process.write(f'REPLACE {data["serial"]} {encode_text(replacement)}\n'.encode('ascii'))
            else:self.cancel();return

    def _finished(self,process):
        if self.process is process:self.process=None;self.timeout.stop()
        process.deleteLater()

    def cancel(self):
        self.revision=getattr(self,'revision',0)+1
        self.timeout.stop();process=self.process;self.process=None
        if process:
            process.write(b'QUIT\n')
            QTimer.singleShot(250,lambda:self._kill(process))

    @staticmethod
    def _kill(process):
        try:
            if process.state()!=QProcess.ProcessState.NotRunning:process.kill()
        except RuntimeError:pass
