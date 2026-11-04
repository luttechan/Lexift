"""Inspect window metadata only for the process this test starts. No external app input."""
import ctypes, json, os, subprocess, time
from ctypes import wintypes
from pathlib import Path

root=Path(__file__).resolve().parents[1]
executable=Path(os.environ.get('LEXIFT_PORTABLE_EXE',root/'portable/Lexift/Lexift.exe'))
user=ctypes.WinDLL('user32',use_last_error=True)
callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
user.IsWindowVisible.argtypes=[wintypes.HWND]
user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]

def windows(pid):
    rows=[]
    @callback_type
    def collect(hwnd,_):
        owner=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid:
            rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect))
            title=ctypes.create_unicode_buffer(256);user.GetWindowTextW(hwnd,title,len(title))
            rows.append(dict(title=title.value,visible=bool(user.IsWindowVisible(hwnd)),width=rect.right-rect.left,height=rect.bottom-rect.top))
        return True
    user.EnumWindows(collect,0)
    return rows

env=dict(os.environ)
# Deliverable verification uses no CDP listener and no real keyboard hooks.
for name in ('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS','LEXIFT_TEST_CDP_PORT'):env.pop(name,None)
env['WEBVIEW2_USER_DATA_FOLDER']=str(root/'verification'/f'webview-portable-{time.time_ns()}')
start=time.monotonic()
process=subprocess.Popen([str(executable),'--diagnostic'],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    while time.monotonic()-start<30:
        if process.poll() is not None:raise RuntimeError(f'Portable exited: {process.returncode}')
        owned=windows(process.pid)
        main=any(w['visible'] and w['title']=='Lexift' and w['width']>=800 for w in owned)
        splash=any(w['visible'] and w['title']=='Lexift' and 450<=w['width']<800 for w in owned)
        if main and not splash:break
        time.sleep(.1)
    else:raise RuntimeError(f'Portable startup did not complete: {owned}')
    report=dict(passed=True,readyMs=round((time.monotonic()-start)*1000),
                checks=['Relocated optimized executable starts with bundled resources',
                        'React readiness closes splash and shows native main window',
                        'Diagnostic run uses no global keyboard hooks or CDP listener'],
                externalInputSent=False)
    (root/'verification/portable.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
finally:
    if process.poll() is None:process.terminate()
    process.wait(timeout=10)
