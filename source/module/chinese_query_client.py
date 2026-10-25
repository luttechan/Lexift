"""Run dictionary loading and phonetic search outside Qt's GUI thread."""
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt

# Keep a thread alive through asynchronous shutdown even if its client loses
# its parent during an application close. No input or history is stored here.
_running_threads=set()


class SearchThread(QThread):
    result = Signal(int, dict)
    failed = Signal(str)
    ready = Signal()

    def __init__(self):
        super().__init__()
        import threading
        self.condition = threading.Condition()
        self.pending = None
        self.closed = False

    def submit(self, serial, text, output_mode='zh'):
        with self.condition:
            self.pending=(serial,text,output_mode)
            self.condition.notify()

    def finish(self):
        with self.condition:
            self.closed=True; self.pending=None; self.condition.notify()

    def run(self):
        try:
            from chinese_reading import ChineseEngine
            engine=ChineseEngine()
            from chinese_variants import OutputProfiles
            profiles=OutputProfiles()
            self.ready.emit()
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.closed or self.pending is not None)
                    if self.closed:
                        return
                    serial,text,output_mode=self.pending; self.pending=None
                self.result.emit(serial,profiles.transform(engine.query(text),output_mode))
        except Exception:
            self.failed.emit('중국어 로컬 사전을 불러오거나 검색하지 못했습니다.')
        finally:
            if 'engine' in locals():engine.close()


class ChineseQueryClient(QObject):
    result=Signal(int,dict)
    failed=Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial=0; self.closed=False;self.ready=False
        self.thread=SearchThread()
        self.thread.result.connect(self._result)
        self.thread.failed.connect(self._failed)
        self.thread.ready.connect(self._ready)
        # Release the keep-alive before queued deleteLater callbacks can delete
        # the client/context. A queued lambda capturing self can otherwise be
        # discarded, permanently retaining an already-finished QThread wrapper.
        self.thread.finished.connect(lambda thread=self.thread:_running_threads.discard(thread),
                                     Qt.ConnectionType.DirectConnection)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.deleteLater)

    def start(self):
        _running_threads.add(self.thread)
        self.thread.start()

    def request(self, text, output_mode='zh'):
        if self.closed or not text:
            return
        self.serial+=1
        self.thread.submit(self.serial,text,output_mode)
        return self.serial

    def cancel(self):
        self.serial+=1
        with self.thread.condition:
            self.thread.pending=None

    @Slot(int,dict)
    def _result(self, serial, data):
        if not self.closed and serial==self.serial:
            self.result.emit(serial,data)

    @Slot()
    def _ready(self):
        self.ready=True

    @Slot(str)
    def _failed(self, message):
        if not self.closed:
            self.failed.emit(message)

    def stop(self):
        if not self.closed:
            self.closed=True; self.thread.finish()
