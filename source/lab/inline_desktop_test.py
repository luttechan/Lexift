"""Temporary interactive test harness, launched on the user's desktop."""
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'module'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from ime_inline import InlineMode
qt=QApplication([]);qt.setQuitOnLastWindowClosed(False)
mode=InlineMode();mode.toggle('zh')
path=root/'test-results'/'inline-desktop-state.json'
command=root/'test-results'/'inline-desktop-command.json'
command.unlink(missing_ok=True)
history=[]
def inspect():
    result={'enabled':mode.enabled,'snapshot':mode.snapshot,'visible':mode.visible(),'replace':mode.last_replace,'query':mode.last_query}
    if not history or history[-1] != mode.snapshot:
        history.append(dict(mode.snapshot))
    result['history']=history[-30:]
    if mode.visible():
        result['candidates']=[mode.list.item(i).text() for i in range(mode.list.count())]
        mode.overlay.grab().save(str(root/'test-results/inline-desktop.png'))
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if command.exists():
        data=json.loads(command.read_text(encoding='utf-8'));command.unlink()
        if data.get('stop'):
            mode.close();QTimer.singleShot(1000,qt.quit)
        if data.get('select') and mode.visible():
            for i in range(mode.list.count()):
                if mode.list.item(i).text()==data['select']:
                    mode.list.setCurrentRow(i);mode.commit();break
timer=QTimer();timer.timeout.connect(inspect);timer.start(200)
QTimer.singleShot(600000,lambda:(mode.close(),QTimer.singleShot(1000,qt.quit)))
qt.exec()
