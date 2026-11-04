#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::{collections::HashMap, io::{BufRead, BufReader, Write}, path::PathBuf, process::{Child, ChildStdin, Command, Stdio}, sync::{Arc, Mutex, atomic::{AtomicBool, AtomicU64, Ordering}}, time::Duration};
use std::os::windows::process::CommandExt;
use tauri::{Emitter, Manager};
use tokio::sync::oneshot;

const MAX_FRAME: usize = 16 * 1024 * 1024;
type Reply = oneshot::Sender<Result<Value, String>>;

#[derive(Default)]
struct Engine {
    child: Mutex<Option<Child>>,
    input: Mutex<Option<ChildStdin>>,
    pending: Mutex<HashMap<u64, Reply>>,
    sequence: AtomicU64,
    generation: AtomicU64,
    quitting: AtomicBool,
    startup_finished: AtomicBool,
    startup_changed: tokio::sync::Notify,
    error: Mutex<Option<String>>,
    selector: Mutex<Value>,
    popups: Mutex<HashMap<&'static str, Value>>,
}

fn read_frame(reader: &mut impl BufRead) -> Result<Option<Vec<u8>>, String> {
    let mut line = Vec::new();
    loop {
        let buffer = reader.fill_buf().map_err(|e| e.to_string())?;
        if buffer.is_empty() { return if line.is_empty() { Ok(None) } else { Err("Incomplete engine response".into()) }; }
        let end = buffer.iter().position(|&b| b == b'\n');
        let count = end.map_or(buffer.len(), |n| n + 1);
        if line.len() + count > MAX_FRAME { return Err("Engine response exceeds frame limit".into()); }
        line.extend_from_slice(&buffer[..count]);
        reader.consume(count);
        if end.is_some() { return Ok(Some(line)); }
    }
}

fn hide_selector(app: &tauri::AppHandle) {
    hide_surface(app, "selector");
}

fn hide_surface(app: &tauri::AppHandle, label: &'static str) {
    let handle=app.clone();
    let _=app.run_on_main_thread(move || {
        // A delayed hide from an older frame must not hide a reopened menu.
        let engine=handle.state::<Arc<Engine>>();
        let visible = if label=="selector" {
            engine.selector.lock().unwrap()["visible"]==true
        } else {
            engine.popups.lock().unwrap().get(label).is_some_and(|frame|frame["visible"]==true)
        };
        if visible { return; }
        if let Some(window)=handle.get_webview_window(label) {
            if let Ok(hwnd)=window.hwnd() {
                #[link(name="user32")]
                extern "system" { fn ShowWindow(hwnd:isize,command:i32)->i32; }
                // The selector is shown through SetWindowPos(NOACTIVATE).
                // Use the matching Win32 path instead of Tao's visibility cache.
                unsafe { ShowWindow(hwnd.0 as isize,0); }
            }
        }
    });
}

fn clear_popups(app:&tauri::AppHandle, engine:&Engine) {
    engine.popups.lock().unwrap().clear();
    for label in ["candidate","notice-popup"] { hide_surface(app,label); }
}

impl Engine {
    fn stop(&self) {
        self.input.lock().unwrap().take();
        if let Some(mut child) = self.child.lock().unwrap().take() { let _ = child.kill(); let _ = child.wait(); }
    }

    fn fail(&self, app: &tauri::AppHandle, generation: u64, message: String) {
        if self.generation.load(Ordering::SeqCst) != generation || self.quitting.load(Ordering::SeqCst) { return; }
        *self.error.lock().unwrap() = Some(message.clone());
        self.stop();
        *self.selector.lock().unwrap() = json!({"visible":false});
        hide_selector(app);
        clear_popups(app,self);
        for (_, reply) in self.pending.lock().unwrap().drain() { let _ = reply.send(Err(message.clone())); }
        let _ = app.emit("engine-error", &message);
    }

    fn start(self: &Arc<Self>, app: tauri::AppHandle) -> Result<(), String> {
        self.startup_finished.store(false, Ordering::Release);
        let result = self.start_process(app);
        if let Err(error) = &result {
            *self.error.lock().unwrap() = Some(error.clone());
        }
        self.startup_finished.store(true, Ordering::Release);
        self.startup_changed.notify_waiters();
        result
    }

    fn start_process(self: &Arc<Self>, app: tauri::AppHandle) -> Result<(), String> {
        let generation = self.generation.fetch_add(1, Ordering::SeqCst) + 1;
        self.stop();
        *self.selector.lock().unwrap() = json!({"visible":false});
        hide_selector(&app);
        clear_popups(&app,self);
        for (_, reply) in self.pending.lock().unwrap().drain() { let _ = reply.send(Err("Engine restarted".into())); }
        *self.error.lock().unwrap() = None;
        let mut path = app.path().resource_dir().map_err(|e| e.to_string())?.join("engine/LexiftEngine.exe");
        if cfg!(debug_assertions) && !path.is_file() { path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../engine-dist/LexiftEngine.exe"); }
        if !path.is_file() { return Err("입력 엔진 파일을 찾을 수 없습니다. 배포 폴더를 확인하세요.".into()); }
        let host = std::env::current_exe().map_err(|e| e.to_string())?;
        let mut command = Command::new(&path);
        command.arg("--host-exe").arg(host).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).creation_flags(0x08000000);
        if std::env::args().any(|arg| arg == "--diagnostic") { command.arg("--diagnostic"); }
        command.env("PYINSTALLER_RESET_ENVIRONMENT", "1");
        command.env("LEXIFT_DESKTOP_PID",std::process::id().to_string());
        for key in ["PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML_IMPORT_PATH", "QML2_IMPORT_PATH"] { command.env_remove(key); }
        let mut child = command.spawn().map_err(|e| format!("입력 엔진 실행 실패: {e}"))?;
        let stdout = child.stdout.take().ok_or("Engine stdout missing")?;
        *self.input.lock().unwrap() = child.stdin.take();
        *self.child.lock().unwrap() = Some(child);
        let engine = Arc::clone(self);
        std::thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            loop {
                let frame = match read_frame(&mut reader) {
                    Ok(Some(frame)) => frame,
                    Ok(None) => { engine.fail(&app, generation, "입력 엔진 연결이 종료되었습니다.".into()); break; }
                    Err(error) => { engine.fail(&app, generation, error); break; }
                };
                if engine.generation.load(Ordering::SeqCst) != generation { break; }
                let message: Value = match serde_json::from_slice(&frame) { Ok(value) => value, Err(_) => { engine.fail(&app, generation, "잘못된 엔진 응답입니다.".into()); break; } };
                if let Some(id) = message.get("id").and_then(Value::as_u64) {
                    if let Some(reply) = engine.pending.lock().unwrap().remove(&id) {
                        let result = if message["ok"] == true { Ok(message["data"].clone()) } else { Err(message["error"].as_str().unwrap_or("Engine command failed").to_string()) };
                        let _ = reply.send(result);
                    }
                } else if let Some(event) = message.get("event").and_then(Value::as_str) {
                    if event == "startup-error" {
                        let reason=message["data"]["message"].as_str()
                            .filter(|reason|!reason.trim().is_empty())
                            .unwrap_or("입력 엔진 연결이 종료되었습니다.");
                        engine.fail(&app,generation,reason.to_owned());
                        break;
                    }
                    if event == "selector" {
                        let frame = message["data"].clone();
                        *engine.selector.lock().unwrap() = frame.clone();
                        if frame["visible"] != true { hide_selector(&app); }
                        let _ = app.emit("engine-selector", frame);
                    }
                    let popup_label=match event { "candidate"=>Some("candidate"), "notice-popup"=>Some("notice-popup"), _=>None };
                    if let Some(label)=popup_label {
                        let frame=message["data"].clone();
                        engine.popups.lock().unwrap().insert(label,frame.clone());
                        if frame["visible"]!=true {hide_surface(&app,label);}
                        let _=app.emit_to(label,"engine-popup",frame);
                    }
                    if event=="tray" { update_tray(&app,message["data"].clone()); }
                    if event=="hide-main" { if let Some(window)=app.get_webview_window("main"){let _=window.hide();} }
                    if event == "navigate" {
                        if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); }
                    }
                    if ["status", "state", "navigate", "notice", "confirm-quit"].contains(&event) { let _ = app.emit(&format!("engine-{event}"), message.get("data").unwrap_or(&Value::Null)); }
                }
            }
        });
        Ok(())
    }

    async fn request(self: &Arc<Self>, action: &str, payload: Value) -> Result<Value, String> {
        // A WebView can ask for state while the native setup is still
        // opening the sidecar's pipes. Wait for that launch to finish.
        tokio::time::timeout(Duration::from_secs(25), self.wait_for_start())
            .await.map_err(|_| "입력 엔진의 응답이 지연되고 있습니다.".to_owned())?;
        if let Some(error) = self.error.lock().unwrap().clone() { return Err(error); }
        let id = self.sequence.fetch_add(1, Ordering::Relaxed) + 1;
        let mut frame = serde_json::to_vec(&json!({"id": id, "action": action, "payload": payload})).map_err(|e| e.to_string())?;
        frame.push(b'\n');
        if frame.len() > MAX_FRAME { return Err("설정 데이터가 너무 큽니다.".into()); }
        let (send, receive) = oneshot::channel();
        { let mut pending = self.pending.lock().unwrap(); if pending.len() >= 64 { return Err("요청이 많습니다. 잠시 후 다시 시도하세요.".into()); } pending.insert(id, send); }
        let engine = Arc::clone(self);
        let written = tauri::async_runtime::spawn_blocking(move || {
            let mut input = engine.input.lock().unwrap();
            let pipe = input.as_mut().ok_or("입력 엔진에 연결되지 않았습니다.")?;
            pipe.write_all(&frame).and_then(|_| pipe.flush()).map_err(|e| e.to_string())
        }).await.map_err(|e| e.to_string())?;
        if let Err(error) = written {
            self.pending.lock().unwrap().remove(&id);
            return Err(self.error.lock().unwrap().clone().unwrap_or(error));
        }
        match tokio::time::timeout(Duration::from_secs(25), receive).await {
            Ok(Ok(result)) => result,
            _ => { self.pending.lock().unwrap().remove(&id); Err("입력 엔진의 응답이 지연되고 있습니다.".into()) }
        }
    }

    async fn wait_for_start(&self) {
        loop {
            let changed = self.startup_changed.notified();
            tokio::pin!(changed);
            changed.as_mut().enable();
            if self.startup_finished.load(Ordering::Acquire) { return; }
            changed.await;
        }
    }
}

#[tauri::command]
async fn engine_command(engine: tauri::State<'_, Arc<Engine>>, action: String, payload: Option<Value>) -> Result<Value, String> {
    if !["get_state", "set_enabled", "set_feature", "set_shortcut", "save_slots", "save_dictionary", "set_general", "reset_defaults", "check_update", "selector_present", "selector_pick", "selector_dismiss", "diagnostic_selector", "candidate_pick", "tray_action", "diagnostic_popup"].contains(&action.as_str()) { return Err("지원하지 않는 요청입니다.".into()); }
    if action.starts_with("diagnostic_") && !std::env::args().any(|arg| arg=="--diagnostic") { return Err("Diagnostic mode required".into()); }
    engine.inner().request(&action, payload.unwrap_or(json!({}))).await
}

#[tauri::command]
fn selector_snapshot(app: tauri::AppHandle, engine: tauri::State<'_, Arc<Engine>>) -> Value {
    let mut frame=engine.selector.lock().unwrap().clone();
    #[link(name="user32")]
    extern "system" { fn GetForegroundWindow() -> isize; fn IsWindowVisible(hwnd:isize) -> i32; }
    if let Some(window)=app.get_webview_window("selector") {
        if let Ok(hwnd)=window.hwnd() { unsafe {
            frame["nativeFocused"]=json!(GetForegroundWindow()==hwnd.0 as isize);
            frame["nativeVisible"]=json!(IsWindowVisible(hwnd.0 as isize)!=0);
        } }
    }
    frame
}

#[tauri::command]
async fn selector_present(app: tauri::AppHandle, engine: tauri::State<'_, Arc<Engine>>, revision: u64) -> Result<(),String> {
    let frame = engine.selector.lock().unwrap().clone();
    if frame["visible"]!=true || frame["revision"].as_u64()!=Some(revision) { return Ok(()); }
    let window=app.get_webview_window("selector").ok_or("Selector missing")?;
    let monitors=window.available_monitors().map_err(|e|e.to_string())?;
    let cursor=window.cursor_position().map_err(|e|e.to_string())?;
    let monitor=monitors.iter().find(|m| {let p=m.position();let s=m.size();cursor.x>=p.x as f64&&cursor.x<(p.x as f64+s.width as f64)&&cursor.y>=p.y as f64&&cursor.y<(p.y as f64+s.height as f64)}).or_else(||monitors.first()).ok_or("Monitor missing")?;
    let scale=monitor.scale_factor();
    let count=frame["items"].as_array().map_or(0,|a|a.len());
    let columns=frame["columns"].as_u64().unwrap_or(3).max(1) as usize;
    let width=(if columns==1 {440.0_f64} else if columns==2 {540.0} else {680.0}).min(monitor.size().width as f64/scale-32.0);
    let height=(154.0+((count+columns-1)/columns) as f64*102.0).min(monitor.size().height as f64/scale-64.0);
    // A non-focusable window leaves the text caret in the user's application.
    // Keyboard navigation stays in the existing low-level native hook.
    #[link(name="user32")]
    extern "system" {
        fn GetWindowLongPtrW(hwnd:isize,index:i32)->isize;
        fn SetWindowLongPtrW(hwnd:isize,index:i32,value:isize)->isize;
        fn SetWindowPos(hwnd:isize,after:isize,x:i32,y:i32,width:i32,height:i32,flags:u32)->i32;
    }
    let hwnd=window.hwnd().map_err(|e|e.to_string())?.0 as isize;
    let x=monitor.position().x+((monitor.size().width as f64-width*scale)/2.0) as i32;
    let y=monitor.position().y+((monitor.size().height as f64-height*scale)/2.0) as i32;
    let (done,shown)=oneshot::channel();
    let shared=Arc::clone(engine.inner());
    app.run_on_main_thread(move || { unsafe {
        let current=shared.selector.lock().unwrap();
        if current["visible"]!=true || current["revision"].as_u64()!=Some(revision) { let _=done.send(true);return; }
        let extended=GetWindowLongPtrW(hwnd,-20);
        SetWindowLongPtrW(hwnd,-20,extended|0x08000000|0x00000080); // NOACTIVATE | TOOLWINDOW
        let result=SetWindowPos(hwnd,-1,x,y,(width*scale).round() as i32,(height*scale).round() as i32,0x0010|0x0020|0x0040); // NOACTIVATE | FRAMECHANGED | SHOWWINDOW
        let _=done.send(result!=0);
    } }).map_err(|e|e.to_string())?;
    if !shown.await.unwrap_or(false) { return Err("Selector display failed".into()); }
    engine.inner().request("selector_present",json!({"revision":revision})).await?;
    Ok(())
}

#[tauri::command]
fn popup_snapshot(window:tauri::WebviewWindow,engine:tauri::State<'_,Arc<Engine>>) -> Value {
    let mut frame=engine.popups.lock().unwrap().get(window.label()).cloned().unwrap_or(json!({"visible":false}));
    #[link(name="user32")]
    extern "system" { fn IsWindowVisible(hwnd:isize)->i32; fn GetForegroundWindow()->isize; }
    if let Ok(hwnd)=window.hwnd() {
        frame["nativeVisible"]=json!(unsafe { IsWindowVisible(hwnd.0 as isize) }!=0);
        frame["nativeFocused"]=json!(unsafe { GetForegroundWindow() }==hwnd.0 as isize);
    }
    frame
}

#[tauri::command]
async fn popup_present(window:tauri::WebviewWindow,app:tauri::AppHandle,engine:tauri::State<'_,Arc<Engine>>,revision:u64) -> Result<(),String> {
    let label=match window.label() {
        "candidate"=>"candidate",
        "notice-popup"=>"notice-popup",
        _=>return Err("Invalid popup window".into()),
    };
    let Some(frame)=engine.popups.lock().unwrap().get(label).cloned() else {return Ok(());};
    if frame["visible"]!=true || frame["revision"].as_u64()!=Some(revision) {return Ok(());}
    let cursor=window.cursor_position().map_err(|e|e.to_string())?;
    let point_x=frame["x"].as_i64().and_then(|v|i32::try_from(v).ok()).unwrap_or(cursor.x as i32);
    let point_y=frame["y"].as_i64().and_then(|v|i32::try_from(v).ok()).unwrap_or(cursor.y as i32);
    let monitors=window.available_monitors().map_err(|e|e.to_string())?;
    let monitor=monitors.iter().find(|monitor|{
        let position=monitor.position();
        let size=monitor.size();
        point_x>=position.x && point_x<position.x+size.width as i32 &&
            point_y>=position.y && point_y<position.y+size.height as i32
    }).or_else(||monitors.first()).ok_or("Monitor missing")?;
    let area=monitor.work_area();
    let scale=monitor.scale_factor();
    let count=frame["values"].as_array().map_or(0,|values|values.len()).min(6);
    let (logical_width,logical_height)=if label=="candidate" {(350,92+count*38)}
        else if frame["placement"]=="corner" {(372,118)} else {(300,60)};
    let scale_ratio=scale/window.scale_factor().unwrap_or(scale);
    let (frame_width,frame_height)=match (window.outer_size(),window.inner_size()) {
        (Ok(outer),Ok(inner))=>(outer.width.saturating_sub(inner.width),outer.height.saturating_sub(inner.height)),
        _=>(0,0),
    };
    let width=((logical_width as f64*scale+frame_width as f64*scale_ratio).round() as i32).min(area.size.width as i32);
    let height=((logical_height as f64*scale+frame_height as f64*scale_ratio).round() as i32).min(area.size.height as i32);
    let (left,top)=(area.position.x,area.position.y);
    let (right,bottom)=(left+area.size.width as i32,top+area.size.height as i32);
    let (x,y)=if label=="candidate" {
        let above=frame["caretHeight"].as_i64().unwrap_or(20).clamp(0,200) as i32;
        (point_x,if point_y+height+4<=bottom {point_y+4} else {point_y-above-height-4})
    } else {
        match frame["placement"].as_str() {
            Some("cursor")=>(point_x+18,point_y+24),
            Some("corner")=>(right-width-16,bottom-height-16),
            Some("bottom")=>(left+(right-left-width)/2,bottom-height-80),
            _=>(left+(right-left-width)/2,top+(bottom-top-height)/2),
        }
    };
    let (x,y)=(x.clamp(left,right-width),y.clamp(top,bottom-height));
    let hwnd=window.hwnd().map_err(|e|e.to_string())?.0 as isize;
    let shared=Arc::clone(engine.inner());
    let (done,shown)=oneshot::channel();
    app.run_on_main_thread(move || {
        let current=shared.popups.lock().unwrap();
        let Some(frame)=current.get(label) else {let _=done.send(false);return;};
        if frame["visible"]!=true || frame["revision"].as_u64()!=Some(revision) {let _=done.send(false);return;}
        #[link(name="user32")]
        extern "system" {
            fn GetForegroundWindow()->isize;
            fn GetWindowLongPtrW(hwnd:isize,index:i32)->isize;
            fn SetWindowLongPtrW(hwnd:isize,index:i32,value:isize)->isize;
            fn ShowWindow(hwnd:isize,command:i32)->i32;
            fn SetWindowPos(hwnd:isize,after:isize,x:i32,y:i32,width:i32,height:i32,flags:u32)->i32;
        }
        unsafe {
            if let Some(target)=frame["hwnd"].as_u64() {
                if target!=GetForegroundWindow() as u64 {
                    ShowWindow(hwnd,0);let _=done.send(false);return;
                }
            }
            let click_through=label=="notice-popup" && frame["kind"]!="notification";
            let style=GetWindowLongPtrW(hwnd,-20)|0x08000080;
            SetWindowLongPtrW(hwnd,-20,if click_through {style|0x20} else {style&!0x20});
            let _=done.send(SetWindowPos(hwnd,-1,x,y,width,height,0x0010|0x0020|0x0040)!=0);
        }
    }).map_err(|e|e.to_string())?;
    if shown.await.unwrap_or(false) && label=="candidate" {
        engine.inner().request("candidate_ack",json!({"revision":revision})).await?;
    }
    Ok(())
}

fn tray_command(app:&tauri::AppHandle,name:String) {
    let engine=Arc::clone(app.state::<Arc<Engine>>().inner());
    let handle=app.clone();
    tauri::async_runtime::spawn(async move {
        if engine.request("tray_action",json!({"name":name})).await.is_err() {
            if name=="quit" {handle.exit(0);}
            else if let Some(window)=handle.get_webview_window("main") {let _=window.show();let _=window.set_focus();}
        }
    });
}

fn update_tray(app:&tauri::AppHandle,frame:Value) {
    let handle=app.clone();
    let _=app.run_on_main_thread(move || {
        use tauri::menu::{CheckMenuItem,Menu,MenuItem,PredefinedMenuItem};
        let Some(tray)=handle.tray_by_id("lexift") else {return;};
        let result=(|| -> tauri::Result<()> {
            let menu=Menu::new(&handle)?;
            let label=|key:&str|frame["items"][key].as_str().unwrap_or(key).to_owned();
            menu.append(&CheckMenuItem::with_id(&handle,"toggle",label("toggle"),true,frame["enabled"]==true,None::<&str>)?)?;
            for key in ["selector","main","settings","about","update","quit"] {
                if ["selector","settings","quit"].contains(&key) {menu.append(&PredefinedMenuItem::separator(&handle)?)?;}
                menu.append(&MenuItem::with_id(&handle,key,label(key),key!="selector" || frame["selector"]==true,None::<&str>)?)?;
            }
            tray.set_menu(Some(menu))?;
            tray.set_tooltip(frame["tooltip"].as_str())?;
            Ok(())
        })();
        if let Err(error)=result {eprintln!("Tray update failed: {error}");}
    });
}

#[tauri::command]
fn ui_ready(app: tauri::AppHandle, show: Option<bool>) {
    if let Some(splash) = app.get_webview_window("splash") { let _ = splash.close(); }
    if show.unwrap_or(true) && !std::env::args().any(|arg| arg == "--background") {
        if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); }
    }
}

#[tauri::command]
fn window_action(app: tauri::AppHandle, action: String) -> Result<(), String> {
    let window = app.get_webview_window("main").ok_or("Window missing")?;
    match action.as_str() {
        "minimize" => window.minimize(),
        "maximize" => if window.is_maximized().unwrap_or(false) { window.unmaximize() } else { window.maximize() },
        "close" => window.hide(),
        _ => return Err("Unknown window action".into()),
    }.map_err(|e| e.to_string())
}

#[tauri::command]
fn restart_engine(app: tauri::AppHandle, engine: tauri::State<'_, Arc<Engine>>) -> Result<(), String> { engine.inner().start(app) }

#[tauri::command]
fn open_external(destination: String) -> Result<(), String> {
    let url = match destination.as_str() {
        "github" => "https://github.com/luttechan/Lexift", "manual" => "https://luttechan.github.io/lexift/guide/1.0.6/ko.html",
        "website" => "https://luttechan.github.io/lexift/", "releases" => "https://github.com/luttechan/Lexift/releases/latest",
        "paypal" => "https://www.paypal.com/ncp/payment/XKVWYK7U2EAB4", _ => return Err("허용되지 않은 주소입니다.".into()) };
    #[link(name="shell32")]
    extern "system" { fn ShellExecuteW(hwnd: isize, operation: *const u16, file: *const u16, parameters: *const u16, directory: *const u16, show: i32) -> isize; }
    let wide: Vec<u16> = url.encode_utf16().chain(Some(0)).collect();
    let result = unsafe { ShellExecuteW(0, std::ptr::null(), wide.as_ptr(), std::ptr::null(), std::ptr::null(), 1) };
    if result <= 32 { return Err("브라우저를 열지 못했습니다.".into()); } Ok(())
}

#[tauri::command]
fn quit_app(app: tauri::AppHandle, engine: tauri::State<'_, Arc<Engine>>) { engine.quitting.store(true, Ordering::SeqCst); engine.stop(); app.exit(0); }

fn main() {
    #[allow(unused_mut)]
    let mut context = tauri::generate_context!();
    // Test-only CDP access is compiled out of optimized delivery builds.
    #[cfg(debug_assertions)]
    if std::env::args().any(|arg| arg == "--diagnostic") {
        if let Ok(port) = std::env::var("LEXIFT_TEST_CDP_PORT").unwrap_or_default().parse::<u16>() {
            if port > 0 { for window in &mut context.config_mut().app.windows {
                window.additional_browser_args = Some(format!("--remote-debugging-port={port} --remote-debugging-address=127.0.0.1"));
            } }
        }
    }
    let engine = Arc::new(Engine::default());
    let runtime_engine = Arc::clone(&engine);
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| { if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); } }))
        .manage(engine)
        .invoke_handler(tauri::generate_handler![engine_command, ui_ready, window_action, restart_engine, open_external, quit_app, selector_snapshot, selector_present, popup_snapshot, popup_present])
        .setup(move |app| {
            use tauri::tray::{MouseButton,TrayIconBuilder,TrayIconEvent};
            let mut tray=TrayIconBuilder::with_id("lexift").tooltip("Lexift").show_menu_on_left_click(false)
                .on_menu_event(|app,event|tray_command(app,event.id().as_ref().to_owned()))
                .on_tray_icon_event(|tray,event|{
                    if let TrayIconEvent::DoubleClick {button:MouseButton::Left,..}=event {
                        tray_command(tray.app_handle(),"main".into());
                    }
                });
            if let Some(icon)=app.default_window_icon() {tray=tray.icon(icon.clone());}
            tray.build(app)?;
            update_tray(app.handle(),json!({"items":{"main":"Lexift","quit":"종료"}}));
            if std::env::args().any(|arg| arg == "--background") { if let Some(splash) = app.get_webview_window("splash") { let _ = splash.hide(); } }
            if let Err(error) = runtime_engine.start(app.handle().clone()) { *runtime_engine.error.lock().unwrap() = Some(error.clone()); let _ = app.emit("engine-error", error); }
            Ok(())
        })
        .on_window_event(|window, event| { if window.label() == "main" { if let tauri::WindowEvent::CloseRequested { api, .. } = event { api.prevent_close(); let _ = window.hide(); } } })
        .build(context).expect("Could not initialize Lexift desktop")
        .run(|app, event| { if let tauri::RunEvent::Exit = event { let engine = app.state::<Arc<Engine>>(); engine.quitting.store(true, Ordering::SeqCst); engine.stop(); } });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn early_state_request_waits_for_startup_outcome() {
        tauri::async_runtime::block_on(async {
            let engine=Arc::new(Engine::default());
            let request=engine.request("get_state",json!({}));
            tokio::pin!(request);
            assert!(tokio::time::timeout(Duration::from_millis(30),request.as_mut()).await.is_err());
            *engine.error.lock().unwrap()=Some("startup failure".into());
            engine.startup_finished.store(true,Ordering::Release);
            engine.startup_changed.notify_waiters();
            assert_eq!(request.await.unwrap_err(),"startup failure");
        });
    }
    #[test] fn bounded_frames_reject_overflow_and_partial_json() {
        let mut long = std::io::Cursor::new(vec![b'x'; MAX_FRAME + 1]); assert!(read_frame(&mut long).is_err());
        let mut partial = std::io::Cursor::new(b"{unfinished".to_vec()); assert!(read_frame(&mut partial).is_err());
        let mut valid = std::io::Cursor::new(b"{}\n{}\n".to_vec()); assert_eq!(read_frame(&mut valid).unwrap().unwrap(), b"{}\n"); assert_eq!(read_frame(&mut valid).unwrap().unwrap(), b"{}\n");
    }
}
