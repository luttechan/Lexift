"""One-shot native replacement: no keystroke history, clipboard, or permanent watcher."""
import json,os
from PySide6.QtCore import QObject,QProcess,QTimer,Signal
from ime_inline import host_path
from ime_query_client import encode_text
from pinyin_tones import apply_tone

def ensure_chinese_latin(hwnd,cancelled=lambda:False,wait=None):
    import threading
    import ime_windows as ime
    wait=wait or (lambda:threading.Event().wait(.02))
    def valid():return not cancelled() and ime.target_is_foreground(hwnd)
    if not valid():return False
    if (ime.current_language(hwnd)&0x3ff)!=4:ime.request_language(hwnd,0x804)
    for _ in range(12):
        if not valid():return False
        if (ime.current_language(hwnd)&0x3ff)==4 and ime.ime_set_native(hwnd,False):return True
        wait()
    return False

class ToneInput(QObject):
    failed=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.process=None;self.buffer=b'';self.target=0;self.tone=0;self.sent=False
        self.timeout=QTimer(self);self.timeout.setSingleShot(True);self.timeout.setInterval(1800)
        self.timeout.timeout.connect(self.cancel)
        self.activation=QTimer(self);self.activation.setInterval(150)
        self.activation.timeout.connect(self._activate_external)
        self.activation_deadline=0

    def prepare_input(self):
        import time
        self.activation_deadline=time.monotonic()+30;self.activation.start()

    def _activate_external(self):
        import time,ctypes
        from ctypes import wintypes
        from ime_windows import get_target_window,user32
        if time.monotonic()>self.activation_deadline:self.activation.stop();return
        hwnd=get_target_window();pid=wintypes.DWORD()
        if hwnd:user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if not hwnd or pid.value==os.getpid():return
        self.activation.stop();self._latin(hwnd)

    def _latin(self,hwnd):
        # The existing activator supplies foreground/cancellation checks and
        # runs bounded IME calls off the GUI thread.
        import threading
        import ime_windows as ime
        revision=getattr(self,'revision',0)
        def run():
            try:
                ok=ensure_chinese_latin(hwnd,lambda:revision!=getattr(self,'revision',0))
            except (OSError,RuntimeError,ime.IMEError):ok=False
            if not ok and revision==getattr(self,'revision',0) and ime.target_is_foreground(hwnd):
                try:self.failed.emit('IME 입력 모드를 확인하지 못했습니다. 입력기 설정을 확인하세요.')
                except RuntimeError:pass
        threading.Thread(target=run,daemon=True,name='Lexift-Pinyin-mode').start()

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
            if data.get('hwnd')!=self.target:self.cancel();return
            source=data.get('source','');replacement=apply_tone(source,self.tone)
            if source and replacement!=source:
                self.sent=True;process.write(f'REPLACE {data["serial"]} {encode_text(replacement)}\n'.encode('ascii'))
            else:self.cancel();return

    def _finished(self,process):
        if self.process is process:self.process=None;self.timeout.stop()
        process.deleteLater()

    def cancel(self):
        self.revision=getattr(self,'revision',0)+1
        self.activation.stop();self.timeout.stop();process=self.process;self.process=None
        if process:
            process.write(b'QUIT\n')
            QTimer.singleShot(250,lambda:self._kill(process))

    @staticmethod
    def _kill(process):
        try:
            if process.state()!=QProcess.ProcessState.NotRunning:process.kill()
        except RuntimeError:pass
