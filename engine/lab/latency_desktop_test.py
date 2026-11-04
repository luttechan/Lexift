"""Opt-in desktop benchmark: mutate only our own Edit; measure first paint.

Launched by latency_desktop_launcher.exe on the interactive desktop. Click its
Edit control. Never modifies another application's document or clipboard.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root.parent/'.builddeps'))
sys.stderr=(root/'test-results/latency-desktop-errors.txt').open('w',encoding='utf-8',buffering=1)
sys.stdout=sys.stderr
sys.path.insert(0,str(root/'module'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from ime_inline import InlineMode
import ime_windows as ime
from korean_activation import KoreanInputActivator
qt=QApplication([]);qt.setQuitOnLastWindowClosed(False)
user=ctypes.WinDLL('user32',use_last_error=True)
kernel=ctypes.WinDLL('kernel32')
kernel.GetTickCount64.restype=ctypes.c_ulonglong
user.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,
    ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
user.CreateWindowExW.restype=wintypes.HWND
user.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
user.SendMessageW.restype=ctypes.c_ssize_t
user.SetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPCWSTR]
user.GetForegroundWindow.restype=wintypes.HWND
user.GetFocus.restype=wintypes.HWND
user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user.SetFocus.argtypes=[wintypes.HWND]
user.SetFocus.restype=wintypes.HWND
window=QWidget();window.setWindowTitle('Lexift latency QA');window.resize(640,220)
body=QVBoxLayout(window);body.addWidget(QLabel('Click the input below. Automatic JP / CN latency test runs only here.'))
area=QWidget();area.setFixedHeight(70);body.addWidget(area)
status=QLabel('Preparing engines…');body.addWidget(status)
edit=user.CreateWindowExW(0x200,'Edit','',0x50000080,6,8,580,40,int(area.winId()),None,None,None)
mode=InlineMode();mode.prepare()
activator=KoreanInputActivator();activation_rows=[];activation_started=False
samples=[('ja','와타시','私'),('ja','니혼고','日本語'),('ja','갓코우','学校'),('ja','쿄우','今日'),('ja','코-히-','コーヒー')]*2
samples += [('zh','니하오','你好'),('zh','셰셰','谢谢'),('zh','워아이니','我爱你'),('zh','베이징','北京'),('zh','짜이젠','再见')]*2
rows=[];active=None;began=0;switched=False;ready_at=time.monotonic();phase='preparing'
observations={};failures=[]
fallback={}
long_rows=[]
long_cases=[('모요-데스','模様です',False),('모요-데스','模様です',True),
            ('센세-데스','先生です',False),('센세-데스','先生です',True),
            ('코-죠-데스','工場です',False),('코-죠-데스','工場です',True)]
mode.failed.connect(failures.append)
report=root/'test-results/latency-desktop.json'
def save():
    report.write_text(json.dumps({'stage':phase,'samples':rows,'first_paint':True,'own_edit_only':True,
        'observations':observations,'failures':failures,'korean_activation':activation_rows,
        'caret_fallback_and_space':fallback,'long_sentence_space':long_rows},ensure_ascii=False,indent=2),encoding='utf-8')

def finish():
    global phase
    phase='complete' if fallback.get('passed') and len(long_rows)==len(long_cases) and all(r.get('passed') for r in long_rows) else 'failed'
    mode.shutdown();save();QTimer.singleShot(800,qt.quit)

def next_long_case():
    global phase,began
    if len(long_rows)==len(long_cases):finish();return
    if user.GetForegroundWindow()!=int(window.winId()):
        QTimer.singleShot(100,next_long_case);return
    source,expected,moved=long_cases[len(long_rows)]
    user.SetFocus(edit)
    full='앞 문장 '+source+' 뒤 문장'
    user.SetWindowTextW(edit,full);end=len('앞 문장 '+source);user.SendMessageW(edit,0xb1,end,end)
    began=time.perf_counter()*1000;phase='long-query';save()

def commit_long(saved,expected,moved):
    global phase
    if phase!='long-ready':return
    latest_serial=mode.snapshot.get('serial')
    # Simulate a Space event queued while geometry updates are in transit.
    if moved:mode.snapshot=saved
    values=[mode.list.item(i).text() for i in range(mode.list.count())]
    if expected not in values:return
    phase='long-replace'
    long_rows.append({'source':saved['source'],'expected':expected,'geometry_changed':moved,
                      'requested_serial':saved['serial'],'latest_serial':latest_serial,'passed':False})
    mode.navigate(0x20);save()

def fallback_test():
    global phase,began
    if user.GetForegroundWindow()!=int(window.winId()):
        QTimer.singleShot(100,fallback_test);return
    if mode.language!='ja':
        mode.toggle('ja');QTimer.singleShot(300,fallback_test);return
    user.SetFocus(edit);user.DestroyCaret()
    full='앞 문장 센세이 뒤 문장';user.SetWindowTextW(edit,full);user.SendMessageW(edit,0xb1,len('앞 문장 센세이'),len('앞 문장 센세이'))
    began=time.perf_counter()*1000;phase='caret-fallback';save()

def activated(ok):
    activation_rows.append({'from':'Korean IME Latin mode','passed':bool(ok and ime.current_language(edit)==ime.LANG_KO and ime.korean_is_hangul(edit) is True)})
    save();QTimer.singleShot(100,next_sample)
activator.finished.connect(activated)
def next_sample():
    global active,began,phase,observations,activation_started
    if len(rows)>=len(samples):
        fallback_test();return
    if user.GetForegroundWindow()!=int(window.winId()):
        QTimer.singleShot(100,next_sample);return
    if not activation_started:
        activation_started=True;user.SetFocus(edit)
        ime.request_language(edit,ime.LANG_KO)
        def activate_korean():
            user.SetFocus(edit)
            ime.korean_set(edit,False)
            activation_rows.append({'latin_mode_confirmed':ime.korean_is_hangul(edit) is False})
            activator.activate(edit)
        QTimer.singleShot(150,activate_korean);return
    language,text,expected=samples[len(rows)]
    if not mode.enabled or mode.language!=language:
        mode.toggle(language);QTimer.singleShot(300,next_sample);return
    active=(language,text,expected);phase='measuring'
    observations={}
    user.SetFocus(edit)
    began=time.perf_counter()*1000
    full='앞 문장 '+text
    user.SetWindowTextW(edit,full)
    user.SendMessageW(edit,0xb1,len(full),len(full))
    status.setText(f'{language} {len(rows)+1}/{len(samples)}')
    user.SetFocus(edit)
    save()
def painted(source):
    global active,phase
    if phase=='long-query' and source==long_cases[len(long_rows)][0]:
        expected=long_cases[len(long_rows)][1];moved=long_cases[len(long_rows)][2]
        values=[mode.list.item(i).text() for i in range(mode.list.count())]
        if expected in values:
            mode.list.setCurrentRow(values.index(expected))
            phase='long-ready';saved=dict(mode.snapshot)
            if moved:window.move(window.x()+20,window.y()+10)
            QTimer.singleShot(150 if moved else 0,lambda:commit_long(saved,expected,moved))
        return
    if phase=='caret-fallback' and source=='센세이':
        values=[mode.list.item(i).text() for i in range(mode.list.count())]
        if '先生' in values:
            fallback.update(backend=mode.snapshot.get('backend'),visible=mode.visible(),
                            x=mode.overlay.x(),y=mode.overlay.y())
            mode.list.addItem('日本語こうじょう🏭');mode.list.setCurrentRow(mode.list.count()-1)
            phase='space-replace';mode.navigate(0x20)
        return
    if not active or source!=active[1]:return
    language,text,expected=active
    elapsed=round(time.perf_counter()*1000-began,2)
    observations.setdefault('first_paint_ms',elapsed)
    values=[mode.list.item(i).text() for i in range(mode.list.count())]
    if expected not in values:return
    active=None
    rows.append({'language':language,'source':text,'elapsed_ms':observations['first_paint_ms'],
                 'full_candidates_ms':elapsed,
                 'passed':expected in values,'backend':mode.snapshot.get('backend')})
    save();QTimer.singleShot(180,next_sample)
mode.presented.connect(painted)
def tick():
    global phase
    if phase=='space-replace':
        value=ctypes.create_unicode_buffer(256);user.GetWindowTextW(edit,value,256)
        if value.value=='앞 문장 日本語こうじょう🏭 뒤 문장':
            fallback['passed']=fallback.get('visible') and fallback.get('backend')=='win32-edit-field'
            fallback['space_replaced_only_word']=True;phase='next-long';QTimer.singleShot(150,next_long_case);return
    if phase=='long-replace':
        value=ctypes.create_unicode_buffer(256);user.GetWindowTextW(edit,value,256)
        if value.value=='앞 문장 '+long_rows[-1]['expected']+' 뒤 문장':
            long_rows[-1]['passed']=True;long_rows[-1]['actual']=value.value
            phase='next-long';save();QTimer.singleShot(150,next_long_case);return
    if phase in ('long-query','long-ready','long-replace') and time.perf_counter()*1000-began>4000:
        failures.append('Long sentence Space timeout');finish();return
    if phase in ('space-replace','caret-fallback') and time.perf_counter()*1000-began>4000:
        fallback.update(passed=False,error='fallback or replacement timeout',snapshot=mode.snapshot)
        finish();return
    if phase=='preparing' and mode.engines['ja'].ready and mode.engines['ja'].pending is None and mode.engines['zh'].ready:
        phase='waiting-focus';status.setText('Ready. Click input.');save()
    if phase=='waiting-focus' and user.GetForegroundWindow()==int(window.winId()):
        user.SetFocus(edit)
        if user.GetFocus()==edit:
            phase='starting';QTimer.singleShot(300,next_sample)
    if active:
        if mode.snapshot.get('source')==active[1]:observations.setdefault('observed_ms',round(time.perf_counter()*1000-began,2))
        if mode.last_query and mode.last_query.get('data',{}).get('source')==active[1]:observations.setdefault('queried_ms',round(time.perf_counter()*1000-began,2))
        observations['visible']=mode.visible()
        observations['foreground_is_own']=user.GetForegroundWindow()==int(window.winId())
        observations['focus_is_own_edit']=user.GetFocus()==edit
        observations['reason']=mode.snapshot.get('reason')
        observations['backend']=mode.snapshot.get('backend')
        observations['enabled']=mode.enabled
    if active and time.perf_counter()*1000-began>4000:
        language,text,expected=active
        rows.append({'language':language,'source':text,'elapsed_ms':4000,'passed':False,'error':'timeout','detail':dict(observations)})
        mode.shutdown();phase='failed';save();qt.quit()
    if time.monotonic()-ready_at>600:
        mode.shutdown();qt.quit()
timer=QTimer();timer.timeout.connect(tick);timer.start(30)
window.show();qt.exec();mode.shutdown()
