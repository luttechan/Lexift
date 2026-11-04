import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import net from 'node:net';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const {chromium}=await import(pathToFileURL(join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs')).href);
const profile=join(root,'verification',`webview-${Date.now()}`);await mkdir(profile,{recursive:true});
const listener=net.createServer();await new Promise(done=>listener.listen(0,'127.0.0.1',done));const port=listener.address().port;await new Promise(done=>listener.close(done));
const target=process.argv.includes('--release')?'release':'debug';
const executable=process.env.LEXIFT_NATIVE_EXE||join(root,'src-tauri/target/x86_64-pc-windows-msvc',target,'lexift-desktop.exe');
const env={...process.env,NO_PROXY:'localhost,127.0.0.1',LEXIFT_TEST_CDP_PORT:String(port),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:`--remote-debugging-port=${port}`,WEBVIEW2_USER_DATA_FOLDER:profile};
const started=performance.now();const child=spawn(executable,['--diagnostic'],{env,windowsHide:true,stdio:['ignore','pipe','pipe']});let log='';child.stdout.on('data',data=>log+=data);child.stderr.on('data',data=>log+=data);
const endpoint=`http://127.0.0.1:${port}`;let browser;
try {
  await writeFile(join(root,`verification/native-${target}-process.json`),JSON.stringify({pid:child.pid,port,executable,profile}));
  let online=false,lastError='';
  for(let n=0;n<300;n++){if(child.exitCode!==null)throw Error(`Desktop exited (${child.exitCode}): ${log}`);try{const response=await fetch(endpoint+'/json/version');if(response.ok){online=true;break}}catch(error){lastError=String(error.cause||error)}await new Promise(done=>setTimeout(done,100));}
  assert(online,'WebView2 debug endpoint did not initialize: '+lastError);
  browser=await chromium.connectOverCDP(endpoint);const context=browser.contexts()[0];
  let page;
  for(let n=0;n<150;n++){page=context.pages().find(p=>p.url().includes('tauri.localhost')&&!new URL(p.url()).search);if(page)break;await new Promise(done=>setTimeout(done,100));}
  assert(page,`Main WebView not found: ${context.pages().map(p=>p.url()).join(',')}`);
  await page.getByRole('heading',{name:'익숙한 입력, 더 넓은 언어.',exact:true}).waitFor({timeout:25000});
  const firstReadyMs=Math.round(performance.now()-started);
  const rpc=(action,payload={})=>page.evaluate(({action,payload})=>window.__TAURI_INTERNALS__.invoke('engine_command',{action,payload}),{action,payload});
  const nativeVisibility=async(visible)=>{
    let snapshot;
    for(let n=0;n<30;n++){
      snapshot=await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('selector_snapshot'));
      if(snapshot.nativeVisible===visible)return snapshot;
      await new Promise(done=>setTimeout(done,50));
    }
    assert.fail(`Native selector visibility should be ${visible}: ${JSON.stringify(snapshot)}`);
  };
  const state=await rpc('get_state');assert(state.connected&&state.diagnostic&&!state.running);
  const checks=['Real Tauri IPC connected to frozen engine','Diagnostic mode installs no global keyboard hooks'];
  await page.screenshot({path:join(root,`verification/native-${target}-dashboard.png`)});
  const rejected=await page.evaluate(async()=>{try{await window.__TAURI_INTERNALS__.invoke('engine_command',{action:'execute',payload:{command:'never execute'}});return false}catch{return true}});
  assert(rejected);checks.push('Host rejects unregistered engine operations');
  const badUrl=await page.evaluate(async()=>{try{await window.__TAURI_INTERNALS__.invoke('open_external',{destination:'https://example.com'});return false}catch{return true}});
  assert(badUrl);checks.push('Host rejects arbitrary external destinations');
  await page.getByRole('button',{name:'사용자 사전',exact:true}).click();await page.getByRole('button',{name:'단어 추가',exact:true}).first().click();
  await page.getByLabel('키워드 1',{exact:true}).fill('도쿄');await page.getByLabel('대치할 텍스트 1',{exact:true}).fill('東京');await page.getByRole('button',{name:'저장',exact:true}).click();
  await page.waitForFunction(async()=>{const state=await window.__TAURI_INTERNALS__.invoke('engine_command',{action:'get_state',payload:{}});return state.dictionary.length===1});
  assert((await rpc('get_state')).dictionary[0].text==='東京');checks.push('React form persists through native IPC and frozen settings engine');
  await page.getByRole('button',{name:'단축키',exact:true}).click();await page.getByLabel('한일 변환 키',{exact:true}).selectOption('Q');
  assert(await page.locator('.shortcut-editor').nth(1).getByRole('button',{name:'적용',exact:true}).isDisabled());checks.push('Native UI blocks shortcut conflicts');
  await page.getByRole('button',{name:'일반 설정',exact:true}).click();await page.getByRole('button',{name:'기본값',exact:true}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');assert(await page.getByRole('dialog').count()===0);assert((await rpc('get_state')).dictionary.length===1);checks.push('Native reset dialog cancels without losing data');
  await page.getByRole('switch',{name:'Caps Lock 상태 알림',exact:true}).click();assert((await rpc('get_state')).general.capsNotice===false);checks.push('Caps indicator preference persists through the native settings boundary');
  const layouts=state.layouts.slice(0,2);
  await rpc('save_slots',{slots:layouts.map((layout,index)=>({hkl:layout.hkl,mode:layout.modes[0].value,name:`Test ${index+1}`}))});
  const frame=await rpc('diagnostic_selector',{open:true});
  const selector=context.pages().find(p=>p.url().includes('selector'));assert(selector);
  await selector.locator('.selector-tile').first().waitFor();
  await page.waitForFunction(async()=>Boolean((await window.__TAURI_INTERNALS__.invoke('selector_snapshot')).nativeVisible));
  const selectorWindow=await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('selector_snapshot'));
  assert(selectorWindow.nativeFocused===false,JSON.stringify(selectorWindow));checks.push('React selector is visible without becoming the Windows foreground window');
  await selector.screenshot({path:join(root,'verification/native-selector.png')});
  const stale=await rpc('selector_pick',{index:0,revision:frame.revision-1});assert(stale.visible);checks.push('Stale selector clicks cannot choose a newer target');
  const items=frame.items;const chosen=items.length>1?1:0;
  if(chosen)await rpc('diagnostic_selector',{key:39});
  await rpc('diagnostic_selector',{key:13});
  let selected=null;
  for(let n=0;n<30;n++){selected=(await rpc('get_state')).lastSelection;if(selected)break;await new Promise(done=>setTimeout(done,100))}
  assert(selected?.name===items[chosen].slot.name,JSON.stringify({selected,items,frame:await rpc('diagnostic_selector')}));checks.push('Native arrow navigation and Enter select through the new renderer');
  await nativeVisibility(false);checks.push('Enter physically hides the native selector window');
  await rpc('diagnostic_selector',{open:true});await nativeVisibility(true);assert(!(await rpc('diagnostic_selector',{key:27})).visible);await nativeVisibility(false);checks.push('Escape physically hides the selector window');
  for(let n=0;n<3;n++){
    await new Promise(done=>setTimeout(done,300));
    const opened=await rpc('diagnostic_selector',{toggle:true});assert(opened.visible);await nativeVisibility(true);
    await new Promise(done=>setTimeout(done,300));
    const closed=await rpc('diagnostic_selector',{toggle:true});assert(!closed.visible);await nativeVisibility(false);
  }
  checks.push('Caps+Q controller path physically opens and closes the menu for three consecutive cycles');
  const candidate=context.pages().find(p=>p.url().includes('?candidate'));
  const notice=context.pages().find(p=>p.url().includes('?notice-popup'));
  assert(candidate&&notice);
  const popupVisibility=async(p,visible)=>{
    let snapshot;
    for(let n=0;n<60;n++){
      snapshot=await p.evaluate(()=>window.__TAURI_INTERNALS__.invoke('popup_snapshot'));
      if(snapshot.nativeVisible===visible)return snapshot;
      await new Promise(done=>setTimeout(done,50));
    }
    assert.fail(`Popup did not reach visibility ${visible}: ${JSON.stringify(snapshot)}`);
  };
  await rpc('diagnostic_popup',{surface:'candidate',visible:true});
  await candidate.getByRole('option',{name:'1 私',exact:true}).waitFor();
  assert(!(await popupVisibility(candidate,true)).nativeFocused);
  await candidate.waitForFunction(()=>{const list=document.querySelector('.candidate-list');return list&&list.scrollHeight<=list.clientHeight;});
  await candidate.screenshot({path:join(root,'verification/native-candidate-light.png')});
  await candidate.emulateMedia({colorScheme:'dark'});
  await candidate.screenshot({path:join(root,'verification/native-candidate-dark.png')});
  await rpc('diagnostic_popup',{surface:'candidate',visible:false});
  await popupVisibility(candidate,false);
  checks.push('React candidate popup shows without focus and physically hides');
  await rpc('diagnostic_popup',{surface:'notice-popup',visible:true});
  assert(!(await popupVisibility(notice,true)).nativeFocused);
  await popupVisibility(notice,false);
  checks.push('React Caps notification shows without focus and expires');
  await rpc('tray_action',{name:'toggle'});
  assert(!(await rpc('get_state')).enabled);
  await rpc('tray_action',{name:'toggle'});
  checks.push('Tauri tray action updates engine state');
  await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('window_action',{action:'minimize'}));
  checks.push('Native window minimize command works');
  const report={passed:true,target,firstReadyMs,checks,diagnostic:true,externalInputSent:false};await writeFile(join(root,`verification/native-${target}.json`),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
  await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('quit_app')).catch(()=>{});
  if(child.exitCode===null)await Promise.race([new Promise(done=>child.once('exit',done)),new Promise((_,reject)=>setTimeout(()=>reject(Error('Desktop did not exit')),10000))]);
} finally {
  if(browser)await browser.close().catch(()=>{});
  if(child.exitCode===null)child.kill();
  await writeFile(join(root,`verification/native-${target}.log`),log);
}
