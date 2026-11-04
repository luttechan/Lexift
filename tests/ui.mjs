import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {dirname,join,resolve,sep,extname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const {chromium}=await import(pathToFileURL(join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs')).href);
const catalog=JSON.parse(await readFile(join(root,'src/locales.json'),'utf8'));
const dist=join(root,'dist');const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.ttf':'font/ttf','.woff2':'font/woff2','.png':'image/png'};
const server=createServer(async(req,res)=>{try{const url=new URL(req.url,'http://localhost');const path=resolve(dist,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));if(!path.startsWith(dist+sep))throw Error();const data=await readFile(path);res.writeHead(200,{'Content-Type':mime[extname(path)]||'application/octet-stream'});res.end(data)}catch{res.writeHead(404);res.end()}});
await new Promise(done=>server.listen(0,'127.0.0.1',done));const url=`http://127.0.0.1:${server.address().port}`;
await mkdir(join(root,'verification'),{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const page=await browser.newPage({viewport:{width:1120,height:820}});const errors=[];page.on('pageerror',error=>errors.push(error.message));const checks=[];
const check=(name,value)=>{assert(value,name);checks.push(name)};
const button=name=>page.getByRole('button',{name,exact:true});
async function capture(name){await page.mouse.move(0,0);await page.waitForTimeout(180);await page.screenshot({path:join(root,`verification/${name}.png`)})}
async function contrast(selector){const value=await page.locator(selector).first().evaluate(element=>{
  const rgb=value=>(value.match(/[\d.]+/g)||[]).map(Number);const l=value=>{const c=rgb(value).slice(0,3).map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4});return c[0]*.2126+c[1]*.7152+c[2]*.0722};
  let parent=element,bg='';while(parent){const color=getComputedStyle(parent).backgroundColor;if(rgb(color)[3]!==0){bg=color;break}parent=parent.parentElement}const a=l(bg),b=l(getComputedStyle(element).color);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)
});check(`Readable contrast ${selector}: ${value.toFixed(2)}`,value>=4.5)}
try{
  await page.goto(url+'/?preview=1');await page.getByRole('heading',{name:'익숙한 입력, 더 넓은 언어.'}).waitFor();await page.evaluate(()=>document.fonts.ready);
  check('Preview cannot write real settings',await page.getByText('미리보기에서는 실제 설정을 변경하지 않습니다.').isVisible());await capture('home-light');
  await button('단축키').click();await page.getByLabel('한일 변환 키',{exact:true}).selectOption('Q');check('Conflict blocks apply',await page.locator('.shortcut-editor').nth(1).getByRole('button',{name:'적용'}).isDisabled());
  await page.getByLabel('한일 변환 키',{exact:true}).selectOption('F9');await page.locator('.shortcut-editor').nth(1).getByRole('button',{name:'적용'}).click();
  await button('사용자 사전').click();check('Practical dictionary example',await page.locator('.dictionary-example').innerText().then(text=>text.includes('도쿄')&&text.includes('東京')&&!text.includes('스미네')));
  await button('단어 추가').first().click();await page.getByLabel('키워드 1',{exact:true}).fill('도쿄');await page.getByLabel('대치할 텍스트 1',{exact:true}).fill('東京');
  await button('단어 추가').first().click();await page.getByLabel('키워드 2',{exact:true}).fill('니하오');await page.getByLabel('대치할 텍스트 2',{exact:true}).fill('你好');await button('단어 삭제 1').click();
  check('Individual deletion keeps the other word',await page.getByLabel('키워드 1',{exact:true}).inputValue()==='니하오');await button('저장').click();
  await page.getByLabel('키워드 1',{exact:true}).fill('니-하오');await button('일반 설정').click();
  await page.getByRole('switch',{name:'Caps Lock 상태 알림',exact:true}).click();check('Caps indicator can be disabled',await page.getByRole('switch',{name:'Caps Lock 상태 알림'}).getAttribute('aria-checked')==='false');
  await button('사용자 사전').click();check('Changing another setting preserves unsaved words',await page.getByLabel('키워드 1',{exact:true}).inputValue()==='니-하오');await button('저장').click();
  await button('일반 설정').click();await button('기본값').click();await page.keyboard.press('Escape');await button('사용자 사전').click();check('Escape cancels reset',await page.getByLabel('키워드 1',{exact:true}).inputValue()==='니-하오');
  await page.emulateMedia({colorScheme:'dark'});await button('홈').click();await contrast('h1');await contrast('.feature-card h3');await contrast('.slot-chips strong');await capture('home-dark');
  for(const [name,file] of [['입력 언어','inputs'],['단축키','shortcuts'],['사용자 사전','dictionary'],['일반 설정','settings'],['프로그램 정보','about']]){
    await button(name).click();await contrast('h1');await capture(`${file}-dark`);
    if(file==='dictionary')await contrast('.dictionary-row input');
    if(file==='settings'){await button('기본값').click();await contrast('.dialog h2');await contrast('.dialog .button:not(.secondary)');await capture('dialog-dark');await page.keyboard.press('Escape')}
  }
  let language='ko';
  const expectedConfirmation={
    ko:'표시 언어를 영어로 바꿀까요?',
    en:'Switch the display language to Japanese?',
    ja:/^表示言語を(?:簡体中国語|中国語 \(簡体字\))に変更しますか？$/,
    zh_CN:/^要将界面语言切换为(?:繁体中文|中文（繁体）)吗？$/,
    zh_TW:'要將介面語言切換為法文嗎？',
    fr:'Passer l’interface en espagnol ?',
    es:'¿Cambiar el idioma de la interfaz a ruso?',
    ru:'Переключить интерфейс на немецкий?',
    de:'Die Anzeigesprache auf Koreanisch umstellen?',
  };
  for(const next of ['en','ja','zh_CN','zh_TW','fr','es','ru','de','ko']){
    await button(catalog[language]['일반 설정']).click();await page.getByRole('combobox').selectOption(next);await page.getByRole('dialog').waitFor();
    if(expectedConfirmation[language]){
      check(`Natural language confirmation ${language}: ${await page.getByRole("dialog").innerText()}`,
        await page.getByRole('dialog').getByText(expectedConfirmation[language],{exact:true}).isVisible());
    }
    if(next==='en'){await page.keyboard.press('Escape');check('Language confirmation cancels correctly',await page.getByRole('combobox').inputValue()==='ko');await page.getByRole('combobox').selectOption(next)}
    await page.getByRole('dialog').getByRole('button',{name:catalog[language]['변경'],exact:true}).click();language=next;
    await button(catalog[language]['홈']).waitFor();await button(catalog[language]['홈']).click();
    check(`Localized heading ${language}`,await page.getByRole('heading',{name:catalog[language]['익숙한 입력, 더 넓은 언어.'],exact:true}).isVisible());
    if(['en','ja','de'].includes(language))await capture(`home-${language}`);
    await page.setViewportSize({width:860,height:700});check(`No overflow in ${language}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await button(catalog[language]['단축키']).click();check(`Localized shortcut labels ${language}`,await page.getByRole('heading',{name:catalog[language]['한일 변환'],exact:true}).isVisible());
    if(language!=='ko')check(`Korean input limitation translated ${language}`,await page.getByText(catalog[language]['발음 변환은 한국어 입력 기준입니다. 다른 키보드 환경에서는 지원하지 않을 수 있습니다.']).isVisible());
    await page.setViewportSize({width:1120,height:820});
  }
  await page.setViewportSize({width:390,height:844});await button('홈').click();check('Compact viewport has no overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await capture('home-compact');
  await page.setViewportSize({width:680,height:300});await page.goto(url+'/?selector&preview=1');await page.locator('.selector-tile').first().waitFor();await page.locator('.selector-tile').nth(1).click();check('React selector renders and updates selection',await page.locator('.selector-tile').nth(1).getAttribute('aria-pressed')==='true');await capture('selector-dark');await page.emulateMedia({colorScheme:'light'});await capture('selector-light');
  await page.setViewportSize({width:520,height:350});await page.goto(url+'/?splash&preview=1');await page.evaluate(()=>document.fonts.ready);check('Local handwritten font loads',await page.evaluate(()=>document.fonts.check('36px Allura')));await capture('splash-light');await page.emulateMedia({colorScheme:'dark'});await capture('splash-dark');
  check('No frontend exceptions',errors.length===0);await writeFile(join(root,'verification/ui.json'),JSON.stringify({passed:true,checks,errors},null,2));console.log(JSON.stringify({passed:true,checks:checks.length}));
}finally{await browser.close();server.close()}
