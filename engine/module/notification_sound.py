"""The supplied notify.wav, outside the GUI thread, with one pending event."""
from pathlib import Path
import logging
import threading
import weakref

_notifier=None

def set_notifier(callback):
    global _notifier
    try:_notifier=weakref.WeakMethod(callback)
    except TypeError:_notifier=weakref.ref(callback)

def notify_event():
    callback=_notifier() if _notifier else None
    if callback:callback()

def sound_path():
    return Path(__file__).resolve().parent/'Style'/'notify.wav'

class NotificationSound:
    def __init__(self,player=None,path=None):
        self.player=player;self.path=Path(path) if path else sound_path()
        self.condition=threading.Condition();self.pending=False;self.closed=False;self.thread=None
    def play(self):
        with self.condition:
            if self.closed:return
            self.pending=True
            if self.thread is None:
                self.thread=threading.Thread(target=self._run,daemon=True,name='Lexift-Sound');self.thread.start()
            self.condition.notify()
    def _run(self):
        if self.player is None:
            import winsound
            self.player=lambda path:winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_NODEFAULT)
        while True:
            with self.condition:
                self.condition.wait_for(lambda:self.closed or self.pending)
                if self.closed:return
                self.pending=False
            try:self.player(self.path)
            except (OSError,RuntimeError):logging.warning('Could not play Lexift notify.wav')
    def close(self):
        with self.condition:
            self.closed=True;self.pending=False;self.condition.notify()
