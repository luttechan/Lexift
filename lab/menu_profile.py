"""Profile owned Qt menu pages without controlling another program."""
import os,sys,tempfile,time,json,cProfile,pstats,io
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root.parent/'.builddeps'),str(root/'module')]
if '--native' not in sys.argv:os.environ['QT_QPA_PLATFORM']='offscreen'
import app
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
qt=QApplication([]);app.choose_font(qt)
rows=[];profiler=cProfile.Profile();profiler.enable()
with tempfile.TemporaryDirectory() as directory,patch.object(app,'available_layouts',return_value=[]):
    store=QSettings(str(Path(directory)/'test.ini'),QSettings.Format.IniFormat)
    started=time.perf_counter();window=app.MainWindow(store,[],False)
    rows.append({'operation':'construct','ms':round((time.perf_counter()-started)*1000,2)})
    for stage in range(2):
        started=time.perf_counter();window._prepare_next_page()
        rows.append({'operation':f'idle prepare {stage}','ms':round((time.perf_counter()-started)*1000,2)})
    window._preferences_timer.stop()
    for index in (0,2,3,0,2,3,1,2,0):
        started=time.perf_counter();window.navigate(index);window.ensurePolished();qt.processEvents()
        rows.append({'operation':f'page {index}','ms':round((time.perf_counter()-started)*1000,2)})
    window._preferences_timer.stop();window.deleteLater();qt.processEvents()
profiler.disable();buffer=io.StringIO();pstats.Stats(profiler,stream=buffer).sort_stats('cumtime').print_stats(18)
(root/'test-results/menu-profile.txt').write_text(buffer.getvalue(),encoding='utf8')
(root/'test-results/menu-latency-final.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows));print(buffer.getvalue())
