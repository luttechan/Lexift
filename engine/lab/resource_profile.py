"""Profile owned Qt pages and conversion clients; no external app automation."""
import os,sys,tempfile,time,json,gc,ctypes
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root.parent/'.builddeps'),str(root/'module')]
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtCore import QSettings,QCoreApplication,QEvent
from PySide6.QtWidgets import QApplication
import app
from custom_dictionary import CustomDictionary
from i18n import set_language
from ime_inline import InlineMode
from chinese_query_client import _running_threads
from runtime_stats import NativeReader
qt=QApplication([]);qt.setQuitOnLastWindowClosed(False);app.choose_font(qt);qt.setStyleSheet(app.QSS)
reader=NativeReader()
user=ctypes.windll.user32
user.GetGuiResources.argtypes=[ctypes.c_void_p,ctypes.c_uint];user.GetGuiResources.restype=ctypes.c_uint
def pump():
    qt.processEvents();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
def wait_for(predicate,timeout=8):
    deadline=time.monotonic()+timeout
    while not predicate():
        if time.monotonic()>deadline:raise RuntimeError('Owned client lifecycle timeout')
        pump();time.sleep(.002)
    pump()
def sample():
    gc.collect();pump()
    return {'private_bytes':reader.read()[1],
            'gdi':user.GetGuiResources(reader.handle,0),'user':user.GetGuiResources(reader.handle,1)}
result={'passed':False,'pages':[],'lifecycle':[],'memory':[]}
with tempfile.TemporaryDirectory() as folder,patch.object(app,'available_layouts',return_value=[]):
    store=QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat)
    dictionary=CustomDictionary(store)
    dictionary.replace([dict(keyword='단어'+chr(0xac00+n),text='澄音',language='ja') for n in range(1000)])
    for iteration in range(60):
        set_language(('ko','en','ja')[iteration%3])
        before=time.perf_counter();window=app.MainWindow(store,[],False)
        if iteration==0:result['construct_ms']=round((time.perf_counter()-before)*1000,2)
        for index in (0,1,2,3,4,0,2,3,4):
            before=time.perf_counter();window.navigate(index);window.ensurePolished();pump()
            if iteration<3:result['pages'].append({'language':app.language(),'page':index,'ms':round((time.perf_counter()-before)*1000,2)})
        if iteration==0:
            window.resize(1100,760);window.navigate(2);pump();window.grab().save(str(root/'test-results/settings-features.png'))
            window.navigate(4);pump();window.grab().save(str(root/'test-results/dictionary-features.png'))
        window._preferences_timer.stop();window.deleteLater();del window;pump()
        if iteration in (9,29,59):result['memory'].append(dict(iteration=iteration+1,**sample()))
    mode=InlineMode();base_children=len(mode.children())
    for iteration in range(20):
        name='ja' if iteration%2==0 else 'zh'
        mode.prepare(name)
        client=mode.engines[name]
        wait_for(lambda:client.ready)
        mode.release(name)
        try:wait_for(lambda:len(mode.children())==base_children and not _running_threads)
        except RuntimeError:
            print({'cycle':iteration,'children':[type(child).__name__ for child in mode.children()],
                   'baseline':base_children,'threads':len(_running_threads)},flush=True)
            raise
        result['lifecycle'].append({'language':name,'remaining_clients':len(mode.engines),
                                    'remaining_threads':len(_running_threads)})
    mode.shutdown()
    if mode.overlay:mode.overlay.deleteLater()
    mode.deleteLater();pump()
    baseline,last=result['memory'][0],result['memory'][-1]
    result['private_growth_after_warmup']=last['private_bytes']-baseline['private_bytes']
    result['gdi_growth_after_warmup']=last['gdi']-baseline['gdi']
    result['user_growth_after_warmup']=last['user']-baseline['user']
    result['passed']=(result['private_growth_after_warmup']<8*1024*1024 and
                       result['gdi_growth_after_warmup']<=3 and result['user_growth_after_warmup']<=3 and
                       all(not r['remaining_clients'] and not r['remaining_threads'] for r in result['lifecycle']))
(root/'test-results/resources-final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('pages','lifecycle')},indent=2))
raise SystemExit(0 if result['passed'] else 1)
