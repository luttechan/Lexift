"""Real TSF queries and two independently configurable shortcut registrations."""
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'module'))
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from ime_panel import CandidatePanel
from isolated_hotkeys import CapsQHook
from hotkeys_windows import HotkeyBinding
from ime_windows import user32

qt=QApplication([]); qt.setQuitOnLastWindowClosed(False)
results={'worker_registration': [], 'live_queries': []}
for selector, ime in [(('caps','Q'),('caps','J')), (('caps','Q'),('ctrl_shift','F11')),
                      (('ctrl_shift','F12'),('caps','A')), (('ctrl_shift','F12'),('ctrl_alt','J'))]:
    hook=CapsQHook(lambda _:None,HotkeyBinding(*selector),on_ime=lambda _:None,ime_binding=HotkeyBinding(*ime))
    try:
        hook.start()
        results['worker_registration'].append({'selector':selector,'ime':ime,'passed':True})
    finally:
        hook.stop()

panel=CandidatePanel(); panel.open()
QTest.qWait(300)
focus_before=user32.GetForegroundWindow()
for text, expected in [('와타시','私'),('니혼고','日本語'),('갓코우','学校'),('쿄우','今日'),('코-히-','コーヒー')]:
    start=time.monotonic()
    panel.search.setText(text)
    while time.monotonic()-start<6 and panel.displayed != text:
        QTest.qWait(20)
    values=[panel.candidates.item(i).text() for i in range(panel.candidates.count())]
    result={'source':text,'reading':panel.reading.text(),'candidates':values,'elapsed_ms':round((time.monotonic()-start)*1000),
            'search_focus_preserved':panel.search.hasFocus(),'passed':expected in values}
    results['live_queries'].append(result)
    assert result['passed'], result
    assert result['search_focus_preserved'], result
    if text=='와타시':
        panel.window.grab().save(str(root/'test-results/live-search.png'))

# Last Hangul syllable is still preedit, as with physical Korean IME typing.
panel.search.setText('와타'); panel.search.setCursorPosition(2)
QCoreApplication.sendEvent(panel.search,QInputMethodEvent('시',[]))
start=time.monotonic()
while time.monotonic()-start<6 and panel.displayed!='와타시': QTest.qWait(20)
assert panel.displayed=='와타시'
assert any(panel.candidates.item(i).text()=='私' for i in range(panel.candidates.count()))
results['uncommitted_last_syllable']=True

# Edit while the old query is running, then clear: no stale candidates survive.
QCoreApplication.sendEvent(panel.search,QInputMethodEvent('',[]))
panel.search.setText('와타시'); QTest.qWait(210)
panel.search.setText('니혼고'); QTest.qWait(30); panel.search.clear()
QTest.qWait(1100)
assert panel.candidates.count()==0 and panel._selection()==''
results['stale_query_discarded']=True
results['foreground_preserved']=focus_before==user32.GetForegroundWindow()
assert not panel.toggle()
assert panel.toggle()
assert not panel.toggle()
results['toggle_on_off']=True
panel.close()
results['physical_shortcut_tested']=False
(root/'test-results/live-smoke.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=True,indent=2))
