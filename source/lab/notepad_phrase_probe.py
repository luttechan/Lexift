"""Opt-in probe, restricted to the newly created LexiftQA Notepad tab."""
import ctypes,json,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root.parent/'.builddeps'),str(root/'module')]
from ime_inline import InlineMode
from korean_activation import KoreanInputActivator
import ime_windows as ime
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
qt=QApplication([]);qt.setQuitOnLastWindowClosed(False)
ime.user32.GetWindowTextW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_int]
allowed={'고','고치','고치소','고치소-','고치소-사','고치소-사마','모요-데스','고치소-사마데시타'}
def own():
    text=ctypes.create_unicode_buffer(512)
    hwnd=ime.user32.GetForegroundWindow();ime.user32.GetWindowTextW(hwnd,text,512)
    return bool(text.value.startswith('LexiftQA') or text.value.startswith('*LexiftQA'))
class Probe(InlineMode):
    def _show(self,data):
        if own() and self.snapshot.get('source') in allowed:super()._show(data)
mode=Probe();mode.toggle('ja');activator=KoreanInputActivator()
state=root/'test-results/notepad-phrase-state.json';command=root/'test-results/notepad-phrase-command.json'
history=[];status={};started=time.monotonic()
activator.finished.connect(lambda ok:status.update(korean_activated=ok))
def inspect():
    if own():
        data={'snapshot':dict(mode.snapshot),'visible':mode.visible(),'replace':mode.last_replace,
              'candidates':[mode.list.item(n).text() for n in range(mode.list.count())] if mode.list else [],
              'query':mode.last_query,**status}
        if mode.snapshot.get('source') not in allowed:data['snapshot']={'reason':mode.snapshot.get('reason'),'backend':mode.snapshot.get('backend')}
        if not history or history[-1]!=data:history.append(data)
        state.write_text(json.dumps({'current':data,'history':history[-30:]},ensure_ascii=False,indent=2),encoding='utf8')
    if command.exists():
        data=json.loads(command.read_text(encoding='utf8'));command.unlink()
        if data.get('stop'):mode.shutdown();qt.quit();return
        if own():
            if data.get('activate'):activator.activate(ime.get_target_window())
            if data.get('select') and mode.visible():
                for n in range(mode.list.count()):
                    if mode.list.item(n).text()==data['select']:mode.list.setCurrentRow(n);break
            if data.get('space'):mode.navigate(0x20)
    if time.monotonic()-started>600:mode.shutdown();qt.quit()
timer=QTimer();timer.timeout.connect(inspect);timer.start(100)
qt.exec();mode.shutdown()
