"""Measure the owned application and its actual workers with temporary settings."""
import ctypes,json,tempfile,time,gc
from ctypes import wintypes
from pathlib import Path
import app
from PySide6.QtCore import QSettings,Qt
from PySide6.QtWidgets import QApplication

class Counters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD),*[(n,ctypes.c_size_t) for n in ('peak','working','poolpeak','pool','nonpeak','non','page','pagepeak','private','private_working','shared_commit')]]

def memory(pid):
    kernel=ctypes.WinDLL('kernel32');kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000|0x10,False,pid)
    if not handle:return None
    try:
        m=Counters();m.cb=ctypes.sizeof(m)
        query=kernel.K32GetProcessMemoryInfo;query.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
        if not query(handle,ctypes.byref(m),m.cb):return None
        return dict(pid=pid,working_mb=round(m.working/1048576,3),private_commit_mb=round(m.private/1048576,3),private_working_mb=round(m.private_working/1048576,3))
    finally:kernel.CloseHandle(handle)

def verify(output):
    import os
    from isolated_hotkeys import HookService
    from layout_profiles import available_layouts,preferred_mode
    from ime_inline import InlineMode
    qt=QApplication.instance() or QApplication([]);qt.setQuitOnLastWindowClosed(False)
    app.choose_font(qt);qt.setStyleSheet(app.QSS)
    result=dict(passed=False,target_mb=60,stages=[],scope='Main process, keyboard worker, and live candidate host; no working-set trimming')
    service=HookService();mode=None;controller=None
    def wait(ms):
        end=time.monotonic()+ms/1000
        while time.monotonic()<end:qt.processEvents();time.sleep(.003)
    def sample(name):
        pids={os.getpid()}
        if service.process and service.process.poll() is None:pids.add(service.process.pid)
        if mode:
            for client in mode.engines.values():
                process=getattr(client,'process',None)
                if process and process.processId():pids.add(int(process.processId()))
        rows=[memory(pid) for pid in pids];rows=[r for r in rows if r]
        sums={key:round(sum(r[key] for r in rows),3) for key in ('working_mb','private_commit_mb','private_working_mb')}
        result['stages'].append(dict(name=name,processes=rows,total=sums))
    try:
        with tempfile.TemporaryDirectory() as directory:
            store=QSettings(str(Path(directory)/'preferences.ini'),QSettings.Format.IniFormat)
            layouts=available_layouts();slots=[dict(hkl=x.hkl,mode=preferred_mode(x),name=x.name) for x in layouts[:3]]
            store.setValue('profiles/slots_json',json.dumps(slots));original=app.QSettings;app.QSettings=lambda *a:store
            try:controller=app.LexiftController(qt)
            finally:app.QSettings=original
            service.ensure_started();wait(400);sample('background_no_candidate_engines')
            window=controller.window;window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen);window.show();window.navigate(2);window.grab();wait(200);sample('settings_open')
            mode=InlineMode();mode.prepare('ja');wait(1200);sample('japanese_engine_ready')
            mode.close();wait(3400);gc.collect();sample('japanese_released')
            mode.prepare('zh');wait(1200);sample('chinese_engine_ready')
            mode.close();wait(3400);gc.collect();sample('chinese_released')
            result['all_engines_released']=not mode.engines
            idle=result['stages'][0]['total']
            result['goal_private_working_met']=idle['private_working_mb']<=60
            result['goal_total_working_met']=idle['working_mb']<=60
            result['passed']=result['all_engines_released'] and len(result['stages'])==6
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    finally:
        if mode:mode.shutdown()
        service.close()
        if controller:
            controller._shutdown_keyboard();controller.tray.hide();controller.tray.hide_notification()
            if controller._window:controller._window.hide()
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['passed'] else 1
