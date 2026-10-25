"""Owned offscreen menu rendering and resource plateau checks, without user input.

Temporary preferences only. No IME changes, clipboard, real updates, shortcuts,
startup registration or external application interaction.
"""
import ctypes,gc,json,os,sys,tempfile,threading,time
from pathlib import Path
from PySide6.QtCore import QCoreApplication,QEvent,QSettings,Qt
from PySide6.QtWidgets import QApplication,QComboBox,QWidget
import app
from i18n import set_language,tr
from memory_diagnostics import memory
from custom_dictionary import CustomDictionary
from update_ui import UpdateProgress,UpdateResult


class TrayHarness:
    """Use the actual menu factory without installing a system tray icon."""
    _create_tray_menu=app.LexiftController._create_tray_menu
    _style_tray_menu=app.LexiftController._style_tray_menu
    def no_op(self,*args):pass
    set_enabled=show_overlay=show_window=check_updates=request_quit=no_op


def flush(qt):
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    qt.processEvents()


def resources():
    kernel=ctypes.WinDLL('kernel32');user=ctypes.WinDLL('user32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    handle=kernel.GetCurrentProcess();handles=ctypes.c_ulong()
    kernel.GetProcessHandleCount.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    kernel.GetProcessHandleCount(handle,ctypes.byref(handles))
    user.GetGuiResources.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    return dict(**memory(os.getpid()),widgets=len(QApplication.allWidgets()),
                handles=handles.value,gdi=user.GetGuiResources(handle,0),
                user=user.GetGuiResources(handle,1),
                stats_threads=sum(t.name=='Lexift-Diagnostics' for t in threading.enumerate()),
                pointer_types=len(ctypes._pointer_type_cache))


def fixture(directory,code):
    set_language(code)
    store=QSettings(str(Path(directory)/'menus.ini'),QSettings.Format.IniFormat)
    store.setValue('general/sound',False)
    layouts=app.available_layouts()
    assert layouts,'No Windows input layouts available'
    from layout_profiles import preferred_mode
    # Full supported slot count and dictionary size; only visible rows paint.
    slots=[dict(hkl=layouts[n%len(layouts)].hkl,
                mode=preferred_mode(layouts[n%len(layouts)]),name='Input '+str(n+1)) for n in range(15)]
    dictionary=CustomDictionary(store)
    dictionary.replace([dict(keyword='키워드'+chr(0xac00+n),text='候補'+str(n),language='ja') for n in range(1000)])
    window=app.MainWindow(store,slots,False)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.refresh_dashboard(slots)
    window.show();window.grab()
    window._preferences_timer.stop()
    return window,slots,store


def operations(window):
    actions=[]
    for name,index in (('dashboard',0),('slots',1),('general',2),('about',3),('dictionary',4)):
        actions.append((name,lambda index=index:window.navigate(index)))
    for index in range(4):
        actions.append(('general-tab-'+str(index),lambda index=index:(window.navigate(2),window.preferences_tabs.setCurrentIndex(index))))
    def stats():
        window.navigate(3)
        scroll=window.pages.widget(3)
        window.runtime_stats.toggle.setChecked(True)
        window.runtime_stats.details.grab()
        scroll.widget().layout().activate()
        scroll.ensureWidgetVisible(window.runtime_stats.details)
        QApplication.instance().processEvents()
    actions.append(('runtime-details',stats))
    return actions


def verify(output,code='ko',soak=False):
    qt=QApplication.instance() or QApplication([])
    qt.setQuitOnLastWindowClosed(False);app.choose_font(qt);qt.setStyleSheet(app.QSS)
    result=dict(version=app.VERSION,language=code,passed=False,first=[],warm=[],checks={},scope='Owned offscreen Qt widgets; render time includes layout and paint, excludes DWM and external application behaviour')
    window=overlay=None;dialogs=[];failures=[];old_hook=sys.excepthook
    sys.excepthook=lambda kind,value,tb:failures.append(str(value))
    try:
        with tempfile.TemporaryDirectory() as directory:
            window,slots,store=fixture(directory,code)
            actions=operations(window)
            for repeat in range(6):
                for name,action in actions:
                    start=time.perf_counter();action();window.grab()
                    elapsed=round((time.perf_counter()-start)*1000,3)
                    result['first' if repeat==0 else 'warm'].append(dict(menu=name,ms=elapsed))
                    if name=='runtime-details':window.runtime_stats.toggle.setChecked(False)
                    flush(qt)
            overlay=app.Overlay();overlay.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            start=time.perf_counter();overlay.prepare_slots(slots)
            result['selector_prepare_ms']=round((time.perf_counter()-start)*1000,3)
            for name in ('selector-first','selector-repeat'):
                start=time.perf_counter();overlay.rebuild(slots);overlay.show();overlay.grab();overlay.hide()
                result['first'].append(dict(menu=name,ms=round((time.perf_counter()-start)*1000,3)))
                flush(qt)
            # Native popup windows are explicitly kept offscreen too.
            result['dropdowns']=[]
            for name,combo in (('input-layout',window.slot_editor.findChildren(QComboBox)[0]),
                               ('shortcut-modifier',window.shortcut_modifier),('shortcut-key',window.shortcut_key),
                               ('language',window.language_combo)):
                window.navigate(1 if name=='input-layout' else 2)
                window.preferences_tabs.setCurrentIndex(0 if name=='language' else 1)
                view=combo.view();view.window().setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                start=time.perf_counter();combo.showPopup();view.grab();combo.hidePopup()
                result['dropdowns'].append(dict(menu=name,ms=round((time.perf_counter()-start)*1000,3)))
                flush(qt)
            for name,dialog in (('exit',app.QuitConfirmation(window)),
                                ('update-progress',UpdateProgress(tr('업데이트를 확인하는 중...'),False)),
                                ('update-result',UpdateResult(app.VERSION,app.VERSION,tr('최신 버전입니다.')))):
                dialogs.append(dialog);dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                start=time.perf_counter();dialog.show();dialog.grab();dialog.hide()
                result['first'].append(dict(menu=name,ms=round((time.perf_counter()-start)*1000,3)))
            tray=TrayHarness();tray._create_tray_menu()
            menu=tray.tray_menu;dialogs.append(menu)
            menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            start=time.perf_counter();menu.show();menu.grab();menu.hide()
            result['first'].append(dict(menu='tray-context-menu',ms=round((time.perf_counter()-start)*1000,3)))
            flush(qt)
            result['checks']['all_main_menus']=all(r['ms']<100 for r in result['first'] if r['menu'] in ('dashboard','slots','general','about','dictionary'))
            result['checks']['all_first_panels_under_100ms']=all(r['ms']<100 for r in result['first'])
            result['checks']['dropdowns_under_100ms']=all(r['ms']<100 for r in result['dropdowns'])
            result['checks']['warm_menus_under_100ms']=all(r['ms']<100 for r in result['warm'])
            result['checks']['dictionary_rows']=window.dictionary_editor.model.rowCount()==1000
            result['checks']['slot_rows']=len(window.slot_editor.slots)==15
            if soak:
                # Warm changing rows/details/popup infrastructure before baseline.
                samples=[]
                for batch in range(11):
                    for repeat in range(20):
                        from native_language_dialog import _dialog_types
                        _dialog_types()
                        for _,action in actions:action()
                        window.grab();window.runtime_stats.toggle.setChecked(False)
                        editor=window.slot_editor
                        editor.move_slot(0,1);editor.move_slot(1,-1)
                        model=window.dictionary_editor.model
                        row=model.rows[0].copy();model.remove(0);model.add();model.rows[-1]=row
                        overlay.rebuild(slots);overlay.grab()
                        flush(qt)
                    gc.collect();flush(qt)
                    samples.append(dict(cycles=(batch+1)*20,**resources()))
                result['soak']=samples
                baseline=samples[1];tail=samples[-1]
                result['growth']={k:round(tail[k]-baseline[k],3) for k in ('private_commit_mb','private_working_mb','widgets','handles','gdi','user','stats_threads','pointer_types')}
                checks=result['checks'];growth=result['growth']
                checks['no_widget_growth']=growth['widgets']==0
                checks['bounded_handles']=all(growth[k]<=4 for k in ('handles','gdi','user'))
                checks['bounded_private_commit']=growth['private_commit_mb']<=3
                checks['single_stats_worker']=tail['stats_threads']<=1
                checks['stats_sampler_exercised']=window.runtime_stats._sampler.thread is not None
                checks['stable_ctypes_cache']=growth['pointer_types']==0
                checks['no_hidden_sampling']=not window.runtime_stats._sampling
            result['checks']['no_event_errors']=not failures
            result['event_errors']=failures
            result['passed']=all(result['checks'].values())
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    finally:
        sampler=window.runtime_stats._sampler if window else None
        for widget in (*dialogs,overlay,window):
            if widget:widget.hide();widget.deleteLater()
        flush(qt);gc.collect()
        if sampler and sampler.thread:sampler.thread.join(1)
        result['stats_worker_released']=not sampler or not sampler.thread or not sampler.thread.is_alive()
        result['passed']=result['passed'] and result['stats_worker_released']
        sys.excepthook=old_hook;set_language('ko')
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['passed'] else 1


def verify_selector(output,code='ko'):
    """Fresh background-start path: never construct or paint a main window."""
    set_language(code)
    qt=QApplication.instance() or QApplication([]);qt.setQuitOnLastWindowClosed(False)
    start=time.perf_counter();app.choose_font(qt)
    result=dict(version=app.VERSION,language=code,passed=False,
                font_ready_ms=round((time.perf_counter()-start)*1000,3))
    qt.setStyleSheet(app.QSS);overlay=None
    try:
        from layout_profiles import preferred_mode
        layouts=app.available_layouts()
        slots=[dict(hkl=layouts[n%len(layouts)].hkl,mode=preferred_mode(layouts[n%len(layouts)]),name='Input '+str(n+1)) for n in range(15)]
        overlay=app.Overlay();overlay.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        start=time.perf_counter();overlay.prepare_slots(slots)
        result['menu_prepare_ms']=round((time.perf_counter()-start)*1000,3)
        start=time.perf_counter();overlay.rebuild(slots);overlay.show();overlay.grab()
        result['first_ms']=round((time.perf_counter()-start)*1000,3)
        result['passed']=result['first_ms']<100
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    finally:
        if overlay:overlay.hide();overlay.deleteLater();flush(qt)
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['passed'] else 1
