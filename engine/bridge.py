"""Private stdio boundary for the React desktop. No HTTP or arbitrary execution."""
from __future__ import annotations
import argparse,ctypes,json,logging,os,sys,tempfile,threading
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
if not getattr(sys,'frozen',False):sys.path.insert(0,str(ROOT/'module'))
os.environ['QT_QPA_PLATFORM']='windows:fontengine=gdi'
MAX_FRAME=16*1024*1024
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8',newline='\n',line_buffering=True)
OUTPUT=sys.stdout
OUTPUT_LOCK=threading.Lock()

def send(value):
    data=json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n'
    if len(data.encode('utf-8'))>MAX_FRAME:raise ValueError('설정 데이터가 너무 큽니다.')
    with OUTPUT_LOCK:OUTPUT.write(data);OUTPUT.flush()

def event(name,data):send(dict(event=name,data=data))

class UserError(ValueError):pass

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host-exe',required=True);parser.add_argument('--diagnostic',action='store_true');args=parser.parse_args()
    host=Path(args.host_exe).absolute()
    if not host.is_file() or host.suffix.lower()!='.exe':raise ValueError('Invalid desktop host')
    event('status',dict(stage='starting',message='입력 엔진을 준비하고 있습니다.'))
    import app
    from PySide6.QtCore import QObject,Signal,QSettings,QTimer
    from PySide6.QtGui import QGuiApplication
    from custom_dictionary import validate as validate_dictionary
    from layout_profiles import available_layouts,mode_options,sanitized_slots
    from hotkeys_windows import HotkeyBinding,MODES,KEY_LABELS
    from i18n import LANGUAGES,SUPPORTED,language,set_language,tr
    from update_core import strict_json
    qt=QGuiApplication([]);qt.setQuitOnLastWindowClosed(False);qt.setApplicationName('Lexift');qt.setOrganizationName('LuteTools')
    app.setup_logging()
    diagnostic_folder=None
    if args.diagnostic:
        diagnostic_folder=tempfile.TemporaryDirectory(prefix='lexift-desktop-check-')
        settings=QSettings(str(Path(diagnostic_folder.name)/'preferences.ini'),QSettings.Format.IniFormat)
        app.QSettings=lambda *unused:settings
        import preferences
        preferences.migrate_preferences=lambda *unused:False
        app.startup_enabled=lambda:settings.value('general/auto_start',False,type=bool)
        app.set_startup_enabled=lambda enabled:settings.setValue('general/auto_start',bool(enabled))
        set_language('ko')
    else:
        app.load_saved_language()
        def startup(enabled):
            from desktop_startup import set_startup
            set_startup(host,enabled)
        app.set_startup_enabled=startup

    # Keep the already deployed mutex name: old and new shells must never hook
    # the same keyboard simultaneously. Diagnostics install no hooks at all.
    mutex=None
    if not args.diagnostic:
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];kernel.CreateMutexW.restype=ctypes.c_void_p
        ctypes.set_last_error(0)
        mutex=kernel.CreateMutexW(None,False,'Local\\KanaShift-LutteLaurent')
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error()==183:
            kernel.CloseHandle(ctypes.c_void_p(mutex))
            raise UserError('기존 Lexift가 실행 중입니다. 알림 영역에서 종료한 뒤 다시 실행하세요.')

    class Status:
        def setText(self,text):event('notice',dict(message=str(text),kind='info'))

    class View:
        def __init__(self):
            self.status=Status();self.dictionary_editor=SimpleNamespace(status=Status());self.slot_editor=SimpleNamespace(slots=[]);self._first_run=False
        def hide(self):event('hide-main',{})
        def set_runtime_enabled(self,*unused):pass
        def set_feature_states(self,*unused):pass
        def refresh_dashboard(self,*unused):pass
        def update_shortcut_ui(self,*unused):pass
        def update_ime_shortcut_ui(self,*unused):pass
        def update_chinese_shortcut_ui(self,*unused):pass
        def update_traditional_shortcut_ui(self,*unused):pass

    handling_request=False
    class Dialogs:
        @staticmethod
        def warning(parent,title,text,*unused):
            notices.show(text,'notification','corner',4000,title)
            if handling_request:raise UserError(str(text))
        critical=warning
        @staticmethod
        def information(parent,title,text,*unused):
            notices.show(text,'notification','corner',3000,title)
        @staticmethod
        def question(*unused):raise UserError('확인이 필요한 작업입니다.')
    app.QMessageBox=Dialogs

    from desktop_selector import DesktopSelector
    from desktop_surfaces import Notices,CapsIndicator,CursorIndicator,TrayAdapter
    from ime_inline import inline_mode
    notices=Notices(event)
    mode=inline_mode()
    mode.desktop_present=lambda frame:event('candidate',frame)
    app.Overlay=lambda:DesktopSelector(event)
    app.CapsLockIndicator=lambda parent:CapsIndicator(notices,parent)
    app.CursorIndicator=lambda:CursorIndicator(notices)

    class Controller(app.LexiftController):
        startup_error=''
        last_selection=None
        def apply_slot(self,slot):
            if args.diagnostic:self.last_selection=slot
            else:super().apply_slot(slot)
        def _create_window(self):self._window=View()
        def _make_tray(self,qt):return TrayAdapter(notices,qt)
        def _create_tray_menu(self):self.tray_menu=None
        def _style_tray_menu(self):pass
        def _show_conversion_notice(self,language,enabled):
            title=tr({'ja':'한일 변환','zh':'한중 변환','zh_tw':'번체 / 주음부호','zh_bopomofo':'주음부호'}[language])
            notices.show(title+('  ON' if enabled else '  OFF'),'conversion','bottom',1500)
        def _prepare_quit_dialog(self):pass
        def show_window(self,page=0):
            self.overlay.hide();self.overlay._selection_revision+=1;self._cancel_switch()
            event('navigate',dict(page=int(page) if isinstance(page,int) else 0))
        def request_quit(self):
            self.overlay.hide();event('confirm-quit',{})
        def _start_hook(self,**kwargs):
            if not args.diagnostic:super()._start_hook(**kwargs)
        def set_enabled(self,enabled):
            if args.diagnostic:
                self._enabled=bool(enabled);self.publish()
            else:super().set_enabled(enabled)
            self.caps_indicator.set_enabled(not args.diagnostic and self._enabled and self.store.value("general/caps_notice",True,type=bool))
        def _keyboard_ready(self,error):
            self.startup_error=error;super()._keyboard_ready(error);self.publish()
        def _sync_enabled_ui(self):
            if hasattr(self,'updater'):self.publish()
        def _rebuild_window(self,code,**kwargs):
            set_language(code);self.store.setValue('general/ui_language',code);self.store.sync();self.overlay.retranslate();self._style_tray_menu();self.publish()
        def check_updates(self):event('navigate',dict(page=3))
        def publish(self):
            event('state',snapshot(self))
            items={'toggle':tr('Lexift 작동 중' if self._enabled else 'Lexift 비활성화'),
                   'selector':tr('입력기 선택'),'main':tr('메인 창'),'settings':tr('설정'),
                   'about':tr('프로그램 정보'),'update':tr('업데이트 확인'),'quit':tr('종료')}
            event('tray',dict(items=items,enabled=self._enabled,
                             selector=self._enabled and self.features['selector'],
                             tooltip=f"Lexift / {'ON' if self._enabled else 'OFF'} / {self.binding.title}"))

    translation_keys=['대시보드','입력기 슬롯','단축키','일반 설정','프로그램 정보','사용자 사전','언어 스위칭','한글 환경 언어 변환','중국어 성조','사용','적용','삭제','추가','저장','취소','종료','기본값','표시 언어','업데이트 확인','실행할 때 메인 창 표시','시작 알림 표시','알림음 재생','Windows 로그인 시 자동 실행','키워드','대치할 텍스트','언어','입력기 선택','한–일 변환','한–중 변환','한국어','일본어','중국어','영어']

    def snapshot(c):
        layouts=available_layouts()
        shortcuts={name:dict(mode=binding.mode,key=binding.key) for name,binding in [('selector',c.binding),('ja',c.ime_binding),('zh',c.chinese_binding),('zh_tw',c.traditional_binding)]}
        ready=args.diagnostic or c.first_run or not c._enabled or not any(c.features.values()) or c._running
        return dict(selectorRenderer="tauri",lastSelection=c.last_selection,version=app.VERSION,connected=True,diagnostic=args.diagnostic,status='error' if c.startup_error else 'ready' if ready else 'starting',error=c.startup_error,enabled=c._enabled,running=c._running,firstRun=c.first_run,language=language(),features=c.features.copy(),shortcuts=shortcuts,slots=c.slots,layouts=[dict(hkl=x.hkl,name=x.name,tag=x.tag,family=x.family,modes=[dict(value=value,label=tr(label)) for value,label in mode_options(x)]) for x in layouts],dictionary=c.custom_dictionary.entries,general=dict(showDashboard=c.store.value('general/show_dashboard',True,type=bool),startNotice=c.store.value('general/start_notice',True,type=bool),sound=c.store.value('general/sound',True,type=bool),autoStart=app.startup_enabled(),capsNotice=c.store.value("general/caps_notice",True,type=bool)),languages=[dict(value=code,label=name) for code,name in LANGUAGES],translations={key:tr(key) for key in translation_keys})

    event('status',dict(stage='connecting',message='단축키와 입력 환경을 연결하고 있습니다.'))
    controller=Controller(qt)
    controller._window=View()
    if args.diagnostic:controller.caps_indicator.stop()
    if not controller.first_run:controller._start_hook(notify=False)
    controller.publish()

    def boolean(value):
        if type(value) is not bool:raise UserError('설정 값을 확인하세요.')
        return value

    def dispatch(action,payload):
        c=controller
        if action=='get_state':pass
        elif action=='candidate_ack':
            mode.desktop_ack(payload.get('revision'));return True
        elif action=='diagnostic_popup':
            if not args.diagnostic:raise UserError('진단 모드에서만 사용할 수 있습니다.')
            if payload.get('surface')=='notice-popup':
                if payload.get('visible'):notices.show('Caps Lock  ON','caps','center',800)
                else:notices.hide()
            elif payload.get('surface')=='candidate':
                mode.desktop_revision+=1
                frame=dict(visible=bool(payload.get('visible')),revision=mode.desktop_revision,
                           source='와타시',values=['私','わたし'],readings=['わたし','わたし'],
                           row=0,hint='Space / Enter')
                event('candidate',frame)
            else:raise UserError('지원하지 않는 요청입니다.')
            return True
        elif action=='candidate_pick':
            mode.desktop_pick(payload.get('revision'),payload.get('row'));return True
        elif action=='tray_action':
            name=payload.get('name')
            if name=='toggle':c.set_enabled(not c._enabled)
            elif name=='selector':c.show_overlay()
            elif name=='main':c.show_window()
            elif name=='settings':c.show_window(2)
            elif name=='about':c.show_window(3)
            elif name=='update':c.check_updates()
            elif name=='quit':
                c.show_window();c.request_quit()
            else:raise UserError('지원하지 않는 요청입니다.')
            return True
        elif action=='selector_present':
            c.overlay.presented(payload.get('revision'));return c.overlay.frame()
        elif action=='selector_pick':
            c.overlay.select(payload.get('index'),payload.get('revision'));return c.overlay.frame()
        elif action=='selector_dismiss':
            if payload.get('revision')==c.overlay._selection_revision:c.overlay.hide()
            return c.overlay.frame()
        elif action=='diagnostic_selector':
            if not args.diagnostic:raise UserError('진단 모드에서만 사용할 수 있습니다.')
            if payload.get('toggle'):c._hotkey(1)
            if payload.get('open'):c.overlay.open(c.slots,0)
            if 'key' in payload:c.overlay.navigate_virtual_key(int(payload['key']))
            return c.overlay.frame()
        elif action=='set_enabled':c.set_enabled(boolean(payload.get('enabled')))
        elif action=='set_feature':
            name=payload.get('name')
            if name not in c.features:raise UserError('지원하지 않는 기능입니다.')
            c.set_feature_enabled(name,boolean(payload.get('enabled')))
        elif action=='set_shortcut':
            name=payload.get('name')
            if name not in ('selector','ja','zh','zh_tw'):raise UserError('단축키 기능을 확인하세요.')
            binding=HotkeyBinding(payload.get('mode',''),payload.get('key',''))
            others={n:b for n,b in [('selector',c.binding),('ja',c.ime_binding),('zh',c.chinese_binding),('zh_tw',c.traditional_binding)] if n!=name}
            if binding in others.values() or (c.features['tone'] and binding.mode=='caps' and binding.key in '01234'):raise UserError('이미 사용 중인 단축키입니다.')
            {'selector':c.change_shortcut,'ja':c.change_ime_shortcut,'zh':c.change_chinese_shortcut,'zh_tw':c.change_traditional_shortcut}[name](binding)
        elif action=='save_slots':
            slots=payload.get('slots');available={x.hkl:x for x in available_layouts()}
            if not isinstance(slots,list) or not 1<=len(slots)<=15:raise UserError('입력기는 1개에서 15개까지 등록할 수 있습니다.')
            checked=sanitized_slots(slots)
            if len(checked)!=len(slots):raise UserError('입력기 정보를 확인하세요.')
            for slot in checked:
                if slot['hkl'] not in available or slot['mode'] not in {m for m,_ in mode_options(available[slot['hkl']])}:raise UserError('Windows에 설치된 입력기와 모드를 선택하세요.')
                if not slot['name']:raise UserError('입력기 이름을 입력하세요.')
            c.save_slots(checked);c.overlay.prepare_slots(c.slots)
        elif action=='save_dictionary':
            c.custom_dictionary.replace(validate_dictionary(payload.get('entries')))
            from ime_inline import inline_mode
            if inline_mode().enabled:inline_mode()._search()
        elif action=='set_general':
            allowed={'showDashboard':'show_dashboard','startNotice':'start_notice','sound':'sound','capsNotice':'caps_notice'}
            if any(k not in {*allowed,'autoStart','language'} for k in payload):raise UserError('지원하지 않는 설정입니다.')
            for key,value in payload.items():
                if key=='language':
                    if value not in SUPPORTED:raise UserError('지원하지 않는 언어입니다.')
                else:boolean(value)
            for key,value in payload.items():
                if key=='language':
                    if value not in SUPPORTED:raise UserError('지원하지 않는 언어입니다.')
                    c._rebuild_window(value)
                elif key=='autoStart':app.set_startup_enabled(boolean(value))
                else:c.store.setValue('general/'+allowed[key],boolean(value))
            c.store.sync()
            c.caps_indicator.set_enabled(not args.diagnostic and c._enabled and c.store.value('general/caps_notice',True,type=bool))
        elif action=='reset_defaults':
            if payload.get('confirmed') is not True:raise UserError('기본값 복원을 확인하세요.')
            c.reset_defaults()
            c.caps_indicator.set_enabled(not args.diagnostic and c._enabled and c.store.value('general/caps_notice',True,type=bool))
        else:raise UserError('지원하지 않는 요청입니다.')
        return snapshot(c)

    class Requests(QObject):
        received=Signal(object)
        closed=Signal()
    requests=Requests()
    def handle(message):
        nonlocal handling_request
        request_id=message.get('id') if isinstance(message,dict) else None
        try:
            handling_request=True
            if type(request_id) is not int or not 0<request_id<2**53:raise UserError('잘못된 요청 번호입니다.')
            action=message.get('action');payload=message.get('payload',{})
            if not isinstance(action,str) or not isinstance(payload,dict):raise UserError('잘못된 요청입니다.')
            if action=='check_update':
                def update():
                    try:
                        from update_core import latest_release
                        release=latest_release();send(dict(id=request_id,ok=True,data=dict(version=release.version,url=release.page)))
                    except Exception as error:send(dict(id=request_id,ok=False,error=tr(str(error))))
                threading.Thread(target=update,daemon=True,name='Lexift-ReleaseCheck').start();return
            result=dispatch(action,payload);send(dict(id=request_id,ok=True,data=result))
        except Exception as error:
            logging.warning('Desktop command rejected: %s',type(error).__name__)
            send(dict(id=request_id,ok=False,error=tr(str(error))))
        finally:
            handling_request=False
    requests.received.connect(handle);requests.closed.connect(qt.quit)
    def read():
        try:
            while True:
                line=sys.stdin.buffer.readline(MAX_FRAME+1)
                if not line:break
                if len(line)>MAX_FRAME or not line.endswith(b'\n'):break
                requests.received.emit(strict_json(line.decode('utf-8')))
        except Exception:pass
        finally:requests.closed.emit()
    threading.Thread(target=read,daemon=True,name='Lexift-DesktopRequests').start()
    qt.aboutToQuit.connect(controller._shutdown_keyboard)
    result=qt.exec()
    controller.tray.hide();controller.caps_indicator.stop();controller._shutdown_keyboard()
    if mutex:kernel.CloseHandle(ctypes.c_void_p(mutex))
    if diagnostic_folder:diagnostic_folder.cleanup()
    return result

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        if not isinstance(error,UserError):
            logging.exception('Input engine startup failed')
        try:event('startup-error',dict(message=str(error)))
        except Exception:pass
        raise SystemExit(1)
