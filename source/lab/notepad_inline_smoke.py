"""Type Korean in an owned Notepad fixture, show candidates, replace that token."""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import subprocess
import sys
import time
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'module'))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from ime_inline import InlineMode
from ime_windows import user32, INPUT, INPUT_UNION, KEYBDINPUT, INPUT_KEYBOARD, KEYEVENTF_KEYUP, _send_keys, korean_set

qt=QApplication([]);qt.setQuitOnLastWindowClosed(False)
fixture=root/'test-results'/'inline-notepad-fixture.txt'
fixture.write_text('',encoding='utf-8')
child=subprocess.Popen(['notepad.exe',str(fixture)])
callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
user32.EnumWindows.argtypes=[callback,W.LPARAM]
user32.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
user32.GetWindowTextLengthW.argtypes=[W.HWND]
user32.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
user32.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
user32.ShowWindow.argtypes=[W.HWND,C.c_int]
user32.AttachThreadInput.argtypes=[W.DWORD,W.DWORD,W.BOOL]
kernel=C.WinDLL('kernel32');kernel.GetCurrentThreadId.restype=W.DWORD
def find():
    found=[]
    @callback
    def visit(hwnd,_):
        text=C.create_unicode_buffer(1024);user32.GetWindowTextW(hwnd,text,1024)
        if fixture.stem in text.value:found.append(hwnd)
        return True
    user32.EnumWindows(visit,0)
    return found[0] if found else 0

def wait_until(condition,seconds=8):
    start=time.monotonic()
    while time.monotonic()-start<seconds:
        QTest.qWait(40)
        if condition(): return True
    return False

def unicode_text(text):
    events=[]
    for c in text:
        for flags in (4,4|KEYEVENTF_KEYUP):
            events.append(INPUT(INPUT_KEYBOARD,INPUT_UNION(ki=KEYBDINPUT(0,ord(c),flags,0,0))))
    array=(INPUT*len(events))(*events)
    assert user32.SendInput(len(events),array,C.sizeof(INPUT))==len(events)

assert wait_until(lambda:find()),'Notepad window not found'
hwnd=find()
original=user32.GetForegroundWindow()
foreground_thread=user32.GetWindowThreadProcessId(original,None)
own_thread=kernel.GetCurrentThreadId()
attached=foreground_thread!=own_thread and user32.AttachThreadInput(own_thread,foreground_thread,True)
user32.ShowWindow(hwnd,9);user32.SetForegroundWindow(hwnd)
if attached:user32.AttachThreadInput(own_thread,foreground_thread,False)
QTest.qWait(400)
assert user32.GetForegroundWindow()==hwnd
mode=InlineMode()
results={}
try:
    unicode_text('앞 문장 ')
    mode.toggle()
    # Real Korean IME receives ordinary virtual keys; the final 시 stays preedit.
    layouts=(C.c_void_p*64)();user32.GetKeyboardLayoutList.argtypes=[C.c_int,C.POINTER(C.c_void_p)]
    for hkl in layouts[:user32.GetKeyboardLayoutList(64,layouts)]:
        if hkl and hkl&0xffff==0x0412:
            user32.PostMessageW(hwnd,0x50,0,hkl);break
    QTest.qWait(300);korean_set(hwnd,True);QTest.qWait(200)
    for letter in 'dhkxktl':
        assert user32.GetForegroundWindow()==hwnd
        _send_keys(ord(letter.upper()));QTest.qWait(90)
    visible=wait_until(lambda:mode.visible() and mode.snapshot.get('source')=='와타시',10)
    results['snapshot']=mode.snapshot
    results['visible']=visible
    results['notepad_kept_foreground']=user32.GetForegroundWindow()==hwnd
    if mode.visible():
        results['candidates']=[mode.list.item(i).text() for i in range(mode.list.count())]
        mode.overlay.grab().save(str(root/'test-results/inline-candidates.png'))
    assert visible,results
    values=results['candidates'];assert '私' in values,results
    mode.list.setCurrentRow(values.index('私'));mode.commit()
    QTest.qWait(700)
    _send_keys(0x11,ord('S'));QTest.qWait(800)
    results['saved_text']=fixture.read_text(encoding='utf-8-sig')
    assert results['saved_text']=='앞 문장 私',results
    results['passed']=True
finally:
    mode.close();QTest.qWait(300)
    if user32.IsWindow(hwnd) and user32.GetForegroundWindow()==hwnd:
        _send_keys(0x11,ord('S'));QTest.qWait(500)
        user32.PostMessageW(hwnd,0x10,0,0)
    (root/'test-results/notepad-inline.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=True,indent=2))
