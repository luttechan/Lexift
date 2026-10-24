"""Development test: real Korean IME key input only into this owned Edit."""
import ctypes,json,sys,time
from ctypes import wintypes
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root.parent/'.builddeps'),str(root/'module')]
sys.stderr=(root/'test-results/composition-errors.txt').open('w',encoding='utf8',buffering=1)
from ime_inline import InlineMode
from korean_activation import KoreanInputActivator
import ime_windows as ime
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel
qt=QApplication([])
u=ime.user32;i=ime.imm32
u.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
u.CreateWindowExW.restype=wintypes.HWND
u.SetFocus.argtypes=[wintypes.HWND];u.SetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPCWSTR]
u.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM];u.SendMessageW.restype=ctypes.c_ssize_t
u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
i.ImmGetCompositionStringW.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
window=QWidget();window.setWindowTitle('Lexift composition QA');window.resize(700,220)
body=QVBoxLayout(window);body.addWidget(QLabel('Owned Korean IME typing test. Waiting for focus.'))
area=QWidget();area.setMinimumHeight(65);body.addWidget(area)
edit=u.CreateWindowExW(0x200,'Edit','',0x50000080,5,10,640,40,int(area.winId()),None,None,None)
mode=InlineMode();mode.prepare();activator=KoreanInputActivator()
cases=[('고','RH'),('고치','RHCL'),('고치소-','RHCLTH-'),('고치소-사마','RHCLTH-TKAK'),('모요-데스','AHDY-EPTM')]
rows=[];phase='warming';index=0;key_index=0;started=time.monotonic()
activation_attempts=0
report=root/'test-results/composition-probe.json'
def capture():
    value=ctypes.create_unicode_buffer(512);u.GetWindowTextW(edit,value,512)
    c=i.ImmGetContext(edit);text=ctypes.create_unicode_buffer(128)
    size=i.ImmGetCompositionStringW(c,8,text,ctypes.sizeof(text)) if c else -1
    if c:i.ImmReleaseContext(edit,c)
    return {'text':value.value,'selection':int(u.SendMessageW(edit,0xb0,0,0)),
            'composition':text.value if size>0 else '', 'snapshot':dict(mode.snapshot),
            'visible':mode.visible(),'candidates':[mode.list.item(n).text() for n in range(mode.list.count())] if mode.list else []}
def save():report.write_text(json.dumps({'stage':phase,'rows':rows},ensure_ascii=False,indent=2),encoding='utf8')
def next_case():
    global phase,key_index
    if len(rows)==len(cases):
        phase='complete';save();mode.shutdown();QTimer.singleShot(500,qt.quit);return
    if u.GetForegroundWindow()!=int(window.winId()):QTimer.singleShot(100,next_case);return
    u.SetFocus(edit);u.SetWindowTextW(edit,'앞 문장 ');u.SendMessageW(edit,0xb1,5,5)
    key_index=0;phase='typing';QTimer.singleShot(150,type_key)
def type_key():
    global key_index,phase
    if u.GetForegroundWindow()!=int(window.winId()):QTimer.singleShot(100,type_key);return
    keys=cases[len(rows)][1]
    if key_index==len(keys):phase='settling';QTimer.singleShot(600,space);return
    key=keys[key_index];ime._send_keys(0xbd if key=='-' else ord(key));key_index+=1
    QTimer.singleShot(90,type_key)
def space():
    global phase
    row={'source':cases[len(rows)][0],'before_space':capture()};rows.append(row)
    if mode.visible():
        values=row['before_space']['candidates']
        selected=next((n for n,v in enumerate(values) if any('\u3400'<=c<='\u9fff' for c in v)),0)
        mode.list.setCurrentRow(selected);row['selected']=values[selected];mode.navigate(0x20)
    else:ime._send_keys(0x20)
    phase='checking';QTimer.singleShot(600,after_space)
def after_space():
    rows[-1]['after_space']=capture();save();QTimer.singleShot(150,next_case)
def activated(ok):
    global phase,activation_attempts
    if not ok:
        activation_attempts+=1
        if activation_attempts<4:QTimer.singleShot(200,activate);return
        phase='activation-failed';save();qt.quit();return
    mode.toggle('ja');QTimer.singleShot(300,next_case)
activator.finished.connect(activated)
def activate():
    if u.GetForegroundWindow()!=int(window.winId()):QTimer.singleShot(100,activate);return
    u.SetFocus(edit);activator.activate(edit)
def tick():
    global phase
    if phase=='warming' and mode.engines['ja'].ready and mode.engines['ja'].pending is None:phase='waiting-focus';save()
    if phase=='waiting-focus' and u.GetForegroundWindow()==int(window.winId()):
        phase='activating';QTimer.singleShot(250,activate)
    if time.monotonic()-started>180:mode.shutdown();qt.quit()
timer=QTimer();timer.timeout.connect(tick);timer.start(50)
window.show();qt.exec();mode.shutdown()
