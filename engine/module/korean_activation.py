"""Activate Korean Hangul in the captured input field without blocking Qt."""
import threading
from PySide6.QtCore import QObject, Signal
import ime_windows as ime


def ensure_korean(hwnd,cancelled=lambda:False,wait=None):
    wait=wait or (lambda:threading.Event().wait(.02))
    def valid():
        return not cancelled() and ime.target_is_foreground(hwnd)
    if not valid():return False
    if ime.current_language(hwnd)!=ime.LANG_KO:
        ime.request_language(hwnd,ime.LANG_KO)
    toggled=False
    for attempt in range(12):
        if not valid():return False
        if ime.current_language(hwnd)==ime.LANG_KO:
            state=ime.korean_is_hangul(hwnd)
            if state is True:return True
            if ime.korean_set(hwnd,True):return True
            if state is False and not toggled and valid():
                toggled=ime.korean_toggle_key(hwnd)
        elif attempt==3:
            ime.request_language(hwnd,ime.LANG_KO,to_root=True)
        wait()
    return valid() and ime.current_language(hwnd)==ime.LANG_KO and ime.korean_is_hangul(hwnd) is True


class KoreanInputActivator(QObject):
    finished=Signal(bool)

    def __init__(self,parent=None):
        super().__init__(parent);self.revision=0

    def cancel(self):
        self.revision+=1

    def activate(self,hwnd):
        self.cancel();revision=self.revision
        def run():
            try:
                ok=ensure_korean(hwnd,lambda:self.revision!=revision)
            except (OSError,RuntimeError,ime.IMEError):
                ok=False
            if self.revision==revision:
                try:self.finished.emit(ok)
                except RuntimeError:pass
        threading.Thread(target=run,daemon=True,name='Lexift-Korean-input').start()
