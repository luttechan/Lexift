import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { listen } from '@tauri-apps/api/event';
import { ArrowDown, ArrowUp, ArrowUpRight, Bell, BookOpen, Check, ChevronRight, Globe2, Keyboard, LayoutDashboard, LoaderCircle, Minus, Plus, Power, Settings2, Square, Trash2, X } from 'lucide-react';
import { bindingLabel, command, host, native, preview } from './bridge';
import { I18n, useT } from './i18n';
import { Selector } from './Selector';
import { Popup } from './Popup';
import type { Binding, BindingName, Entry, Feature, Page, Slot, Snapshot } from './types';

type Run = (action:string,payload?:Record<string,unknown>)=>Promise<boolean>;
export const names:Record<Feature,string>={selector:'언어 전환',ja:'한일 변환',zh:'한중 변환',zh_tw:'번체 / 주음부호',tone:'병음 성조'};
const navigation=[['dashboard','홈',LayoutDashboard],['slots','입력 언어',Globe2],['shortcuts','단축키',Keyboard],['dictionary','사용자 사전',BookOpen],['settings','일반 설정',Settings2],['about','프로그램 정보',Globe2]] as const;

function Toggle({checked,label,onChange,disabled=false}:{checked:boolean;label:string;onChange:(value:boolean)=>void;disabled?:boolean}) {
  return <button type="button" className={`toggle ${checked?'on':''}`} role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={()=>onChange(!checked)}><span/></button>;
}
function Button({children,onClick,disabled=false,secondary=false}:{children:ReactNode;onClick:()=>void;disabled?:boolean;secondary?:boolean}) {
  return <button type="button" className={`button ${secondary?'secondary':''}`} onClick={onClick} disabled={disabled}>{children}</button>;
}
function Select({label,value,onChange,children,disabled=false}:{label:string;value:string;onChange:(value:string)=>void;children:ReactNode;disabled?:boolean}) {
  return <select aria-label={label} value={value} disabled={disabled} onChange={event=>onChange(event.target.value)} onWheel={event=>event.currentTarget.blur()}>{children}</select>;
}
function Shortcut({binding}:{binding:Binding}) {return <span className="shortcut"><kbd>{bindingLabel(binding.mode)}</kbd><span>+</span><kbd>{binding.key}</kbd></span>}
function Heading({title,description}:{title:string;description?:string}) {return <div className="page-heading"><h1>{title}</h1>{description&&<p>{description}</p>}</div>}
function Confirm({title,description,accept,cancel,confirm}:{title:string;description:string;accept:string;cancel:()=>void;confirm:()=>void}) {
  const t=useT();const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const element=ref.current!;element.showModal();return()=>element.close()},[]);
  return <dialog className="dialog" ref={ref} onCancel={event=>{event.preventDefault();cancel()}} aria-labelledby="confirm-title"><h2 id="confirm-title">{title}</h2><p>{description}</p><div><Button secondary onClick={cancel}>{t('취소')}</Button><Button onClick={confirm}>{accept}</Button></div></dialog>;
}
export function Splash({message,error,retry}:{message?:string;error?:string;retry?:()=>void}) {
  const t=useT();
  return <div className="splash" data-tauri-drag-region><div className="splash-glow"/><div className="splash-brand"><img className="splash-mark" src="/lexift-icon.svg" alt="Lexift" draggable={false}/><p className="handwriting">Shift the Way You Learn.</p></div><div className="splash-status" role="status">{error?<><span className="error-text">{t(error)}</span><div className="splash-error-actions">{retry&&<Button secondary onClick={retry}>{t('다시 연결')}</Button>}{native&&<Button secondary onClick={()=>void host('quit_app')}>{t('종료')}</Button>}</div></>:<><LoaderCircle className="spinning" size={15}/><span>{t(message||'입력 환경 준비 중')}</span></>}</div><span className="splash-caption">LUTTÉ LAURENT</span></div>;
}

export default function App() {
  const [locale,setLocale]=useState('ko');
  const route=new URLSearchParams(location.search);
  if(route.has('candidate'))return <Popup candidate/>;
  if(route.has('notice-popup'))return <Popup candidate={false}/>;
  return <I18n language={locale}>{route.has('selector')?<Selector changeLocale={setLocale}/>:<Desktop changeLocale={setLocale}/>}</I18n>;
}
function Desktop({changeLocale}:{changeLocale:(value:string)=>void}) {
  const t=useT();const splash=new URLSearchParams(location.search).has('splash');
  const [state,setState]=useState<Snapshot|null>(null);const [page,setPage]=useState<Page>('dashboard');
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
  const [confirmation,setConfirmation]=useState<'quit'|'reset'|null>(null);const [languageChoice,setLanguageChoice]=useState('');
  const [resetKey,setResetKey]=useState(0);const initialReady=useRef(false);
  const boot=useCallback(async(restart=false)=>{setError('');try{if(restart)await host('restart_engine');setState(await command('get_state'))}catch(problem){setError(String(problem));void host('ui_ready')}},[]);
  useEffect(()=>{
    let disposed=false;const cleanup:(()=>void)[]=[];
    void(async()=>{
      if(native){
        const unlisten=await Promise.all([
          listen<Snapshot>('engine-state',event=>{
            if(!disposed){setState(event.payload);setError(event.payload.error||'')}
          }),
          listen<string>('engine-error',event=>{if(!disposed){setError(event.payload);void host('ui_ready')}}),
          listen<{message:string}>('engine-notice',event=>{if(!disposed)setNotice(event.payload.message)}),
          listen<{page:number}>('engine-navigate',event=>{if(!disposed)setPage((['dashboard','slots','settings','about','dictionary'] as Page[])[event.payload.page]||'dashboard')}),
          listen('engine-confirm-quit',()=>{if(!disposed)setConfirmation('quit')}),
        ]);
        if(disposed){unlisten.forEach(fn=>fn());return}cleanup.push(...unlisten);
      }
      if(!disposed&&!splash)await boot();
    })();return()=>{disposed=true;cleanup.forEach(fn=>fn())};
  },[boot,splash]);
  useEffect(()=>{if(state){changeLocale(state.language);if(state.error)setError(state.error)}},[state?.language,state?.error,changeLocale]);
  useEffect(()=>{if(!splash&&state&&!initialReady.current&&(state.status==='ready'||state.status==='error')){initialReady.current=true;void host('ui_ready',{show:state.firstRun||state.general.showDashboard||state.diagnostic})}},[state?.status,splash]);
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),6000);return()=>clearTimeout(timer)},[notice]);
  const run:Run=async(action,payload={})=>{if(busy)return false;setBusy(true);try{const result=await command(action,payload);setState(result);setNotice('저장했습니다.');return true}catch(problem){setNotice(String(problem));return false}finally{setBusy(false)}};
  const external=(destination:string)=>void host('open_external',{destination}).catch(problem=>setNotice(String(problem)));
  if(splash||!state)return <Splash error={error} retry={()=>void boot(true)}/>;
  const status=state.diagnostic?'진단 모드':error||state.status==='error'?'연결 오류':!state.enabled?'일시 정지':state.firstRun?'입력 언어 등록 필요':state.running?'사용 준비 완료':state.status==='starting'?'연결 중':'입력 기능 중지';
  return <div className="app-shell">
    <aside className="sidebar"><div className="sidebar-brand" data-tauri-drag-region><img src="/lexift-icon.svg" alt="" draggable={false}/><strong>Lexift</strong><span>1.1</span></div><nav aria-label={t('메뉴')}>{navigation.map(([target,label,Icon])=><button key={target} className={page===target?'active':''} aria-current={page===target?'page':undefined} aria-label={t(label)} title={t(label)} onClick={()=>setPage(target)}><Icon size={19}/><span>{t(label)}</span></button>)}</nav><div className="sidebar-bottom"><span className={`connection-dot ${state.running?'ready':''}`}/>{preview?t('미리보기'):t(status)}<small>Lexift {state.version}</small></div></aside>
    <div className="workspace"><header className="titlebar" data-tauri-drag-region><span className="breadcrumb" data-tauri-drag-region><strong>Lexift</strong><span aria-hidden="true">/</span>{t(navigation.find(([target])=>target===page)![1])}</span><div className="window-actions"><button aria-label={t('최소화')} onClick={()=>void host('window_action',{action:'minimize'})}><Minus size={16}/></button><button aria-label={t('최대화')} onClick={()=>void host('window_action',{action:'maximize'})}><Square size={12}/></button><button aria-label={t('알림 영역으로 닫기')} onClick={()=>void host('window_action',{action:'close'})}><X size={17}/></button></div></header>
      <main className="main-content">
        {preview&&<div className="preview-banner">{t('미리보기에서는 실제 설정을 변경하지 않습니다.')}</div>}
        {error&&<div className="error-banner" role="alert"><span>{t(error)}</span><button onClick={()=>void boot(true)}>{t('다시 연결')}</button></div>}
        <div hidden={page!=='dashboard'}>
          <section className="dashboard-hero">
            <div><span className="dashboard-kicker">LEXIFT / DESKTOP</span><Heading title={t('입력은 그대로.')} description={t('언어 전환부터 발음 변환까지, 키보드 하나로.')}/></div>
            <div className="dashboard-glyphs" aria-hidden="true"><span lang="ko">한</span><span lang="ja">あ</span><span lang="zh-Hant">語</span></div>
          </section>
          {state.firstRun&&<div className="setup-banner"><Globe2 size={22}/><span>{t('사용할 입력 언어를 먼저 등록하세요.')}</span><Button onClick={()=>setPage('slots')}>{t('입력기 추가')}</Button></div>}
          <div className="dashboard-grid">
            <section className="dashboard-features">
          <div className="section-title"><h2>{t('기능')}</h2><button onClick={()=>setPage('shortcuts')}>{t('단축키 설정')}<ChevronRight size={16}/></button></div>
          <div className="feature-grid">{(['selector','ja','zh','zh_tw'] as BindingName[]).map((name,index)=><section className="feature-card" key={name}><div className="feature-top"><span className={`feature-symbol symbol-${index}`}>{['Aa','あ','简','繁'][index]}</span><Toggle checked={state.features[name]} label={t(names[name])} disabled={busy} onChange={enabled=>void run('set_feature',{name,enabled})}/></div><h3>{t(names[name])}</h3><Shortcut binding={state.shortcuts[name]}/></section>)}</div>
            </section>
            <section className="dashboard-side">
          <section className="runtime-card"><div className={`runtime-icon ${state.enabled?'enabled':''}`}><Power size={27}/></div><div className="runtime-copy"><h2>Lexift <span>{state.enabled?'ON':'OFF'}</span></h2><p>{t(status)}</p></div><Toggle checked={state.enabled} label={t('Lexift 사용')} disabled={busy} onChange={enabled=>void run('set_enabled',{enabled})}/></section>
          <div className="section-title"><h2>{t('입력 언어')}</h2><button onClick={()=>setPage('slots')}>{t('편집')}<ChevronRight size={16}/></button></div><div className="slot-chips">{state.slots.map((slot,index)=><div key={index}><kbd>{'1234567890ABCDE'[index]}</kbd><div><strong>{slot.name}</strong><small>{state.layouts.find(layout=>layout.hkl===slot.hkl)?.tag}</small></div></div>)}</div>
            </section>
          </div>
          <p className="home-caption">Shift the Way You Learn.</p>
        </div>
        <div hidden={page!=='slots'}><Slots key={`slots-${resetKey}`} state={state} run={run} busy={busy}/></div>
        <div hidden={page!=='shortcuts'}><Shortcuts key={`keys-${resetKey}`} state={state} run={run} busy={busy}/></div>
        <div hidden={page!=='dictionary'}><Dictionary key={`dict-${resetKey}`} state={state} run={run} busy={busy}/></div>
        <div hidden={page!=='settings'}><Heading title={t('일반 설정')}/><section className="panel settings-panel"><h2>{t('실행')}</h2>{([['showDashboard','실행할 때 메인 창 표시'],['autoStart','Windows 로그인 시 자동 실행']] as const).map(([key,label])=><Setting key={key} label={t(label)} checked={state.general[key]} disabled={busy} change={value=>void run('set_general',{[key]:value})}/>)}</section><section className="panel settings-panel"><h2>{t('알림')}</h2>{([['startNotice','시작 알림 표시'],['sound','알림음 재생'],['capsNotice','Caps Lock 상태 알림']] as const).map(([key,label])=><Setting key={key} label={t(label)} checked={state.general[key]} disabled={busy} change={value=>void run('set_general',{[key]:value})}/>)}</section><section className="panel"><div className="setting-row"><h2>{t('표시 언어')}</h2><Select value={state.language} label={t('표시 언어')} disabled={busy} onChange={setLanguageChoice}>{state.languages.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</Select></div></section><section className="panel danger-panel"><div><h2>{t('기본값')}</h2><p>{t('단축키, 입력 언어와 사전을 초기화합니다.')}</p></div><Button secondary disabled={busy} onClick={()=>setConfirmation('reset')}>{t('기본값')}</Button></section></div>
        <div hidden={page!=='about'}><Heading title={t('프로그램 정보')}/><section className="about-brand panel"><img src="/lexift-logo.png" alt="Lexift"/><p className="handwriting">Shift the Way You Learn.</p><span>Lexift {state.version}</span></section><section className="panel credit-panel"><h2>{t('고마운 분')}</h2><div className="setting-row"><span>Translation (JP) & QA</span><strong>루노</strong></div><p className="muted">© 2026 Lutté Laurent</p></section><div className="link-grid">{[['manual','사용설명서'],['github','GitHub'],['paypal','개발 후원']].map(([destination,label])=><button key={destination} onClick={()=>external(destination)}>{t(label)}<ArrowUpRight size={18}/></button>)}</div><div className="about-bottom"><Button secondary disabled={busy} onClick={()=>void(async()=>{if(!native){setNotice(t('미리보기에서는 실제 설정을 변경하지 않습니다.'));return}setBusy(true);try{const result=await host('engine_command',{action:'check_update',payload:{}}) as {version:string};setNotice(t('최신 버전: {version}',{version:result.version}))}catch(problem){setNotice(String(problem))}finally{setBusy(false)}})()}>{t('업데이트 확인')}</Button><button className="quit-link" onClick={()=>setConfirmation('quit')}>{t('종료')}</button></div></div>
      </main><footer className="statusbar"><span>{t(status)}</span><button onClick={()=>external('manual')}>{t('사용설명서')}<ArrowUpRight size={13}/></button></footer>
    </div>
    {notice&&<div className="toast" role="status"><Bell size={17} aria-hidden="true"/><span>{t(notice)}</span><button aria-label={t('알림 닫기')} onClick={()=>setNotice('')}><X size={16}/></button></div>}
    {confirmation&&<Confirm title={t(confirmation==='quit'?'Lexift를 종료할까요?':'기본값으로 되돌릴까요?')} description={t(confirmation==='quit'?'입력기 전환과 발음 변환이 중지됩니다.':'단축키, 입력 언어와 사전을 초기화합니다.')} accept={t(confirmation==='quit'?'종료':'기본값')} cancel={()=>setConfirmation(null)} confirm={()=>{if(confirmation==='quit')void host('quit_app');else void run('reset_defaults',{confirmed:true}).then(ok=>{if(ok)setResetKey(value=>value+1)});setConfirmation(null)}}/>}
    {languageChoice&&<Confirm title={t('표시 언어 변경')} description={t('표시 언어를 {language}로 바꿀까요?',{language:displayLanguageName(state,languageChoice)})} accept={t('변경')} cancel={()=>setLanguageChoice('')} confirm={()=>{void run('set_general',{language:languageChoice});setLanguageChoice('')}}/>}
  </div>;
}
function displayLanguageName(state:Snapshot,code:string) {
  const locale=state.language.replace('_','-');
  const target=code==='zh_CN'?'zh-Hans':code==='zh_TW'?'zh-Hant':code;
  const fallback=state.languages.find(item=>item.value===code)?.label||code;
  return new Intl.DisplayNames([locale],{type:'language',fallback:'none'}).of(target)||fallback;
}
function Setting({label,checked,disabled,change}:{label:string;checked:boolean;disabled:boolean;change:(value:boolean)=>void}) {return <div className="setting-row"><span>{label}</span><Toggle label={label} checked={checked} disabled={disabled} onChange={change}/></div>}
function SaveBar({dirty,busy,invalid,save}:{dirty:boolean;busy:boolean;invalid?:boolean;save:()=>void}) {
  const t=useT();return <div className="save-row"><span>{dirty?t('저장하지 않은 변경사항이 있습니다.'):t('모든 변경사항이 저장되었습니다.')}</span><Button disabled={!dirty||busy||invalid} onClick={save}><Check size={16}/>{t('저장')}</Button></div>;
}
function Slots({state,run,busy}:{state:Snapshot;run:Run;busy:boolean}) {
  const t=useT();const [draft,setDraft]=useState<Slot[]>(state.slots);const source=JSON.stringify(state.slots);useEffect(()=>setDraft(state.slots),[source]);
  const change=(index:number,patch:Partial<Slot>)=>setDraft(rows=>rows.map((row,n)=>n===index?{...row,...patch}:row));
  const move=(index:number,delta:number)=>setDraft(rows=>{const next=[...rows];[next[index],next[index+delta]]=[next[index+delta],next[index]];return next});
  return <><Heading title={t('입력 언어')} description={t('Windows 입력기를 등록하고 표시 순서를 정하세요.')}/><div className="section-title"><h2>{draft.length} / 15</h2><Button secondary disabled={busy||draft.length>=15||!state.layouts.length} onClick={()=>{const layout=state.layouts[0];setDraft([...draft,{hkl:layout.hkl,mode:layout.modes[0].value,name:layout.name}])}}><Plus size={16}/>{t('입력기 추가')}</Button></div><div className="slot-editor">{draft.map((row,index)=>{const layout=state.layouts.find(item=>item.hkl===row.hkl);return <section className="slot-row panel" key={index}><kbd className="row-number">{'1234567890ABCDE'[index]}</kbd><div className="slot-fields"><Select label={`${t('입력기')} ${index+1}`} value={row.hkl} disabled={busy} onChange={hkl=>{const next=state.layouts.find(item=>item.hkl===hkl)!;change(index,{hkl,mode:next.modes[0].value,name:next.name})}}>{!layout&&<option value={row.hkl}>{t('사용할 수 없는 입력기')}</option>}{state.layouts.map(item=><option key={item.hkl} value={item.hkl}>{item.name}</option>)}</Select><Select label={`${t('입력 모드')} ${index+1}`} value={row.mode} disabled={busy} onChange={mode=>change(index,{mode})}>{layout?.modes.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</Select><input aria-label={`${t('표시 이름')} ${index+1}`} maxLength={32} disabled={busy} value={row.name} onChange={event=>change(index,{name:event.target.value})}/></div><div className="row-tools"><button aria-label={`${t('위로')} ${index+1}`} disabled={busy||index===0} onClick={()=>move(index,-1)}><ArrowUp size={16}/></button><button aria-label={`${t('아래로')} ${index+1}`} disabled={busy||index===draft.length-1} onClick={()=>move(index,1)}><ArrowDown size={16}/></button><button aria-label={`${t('삭제')} ${index+1}`} disabled={busy||draft.length===1} onClick={()=>setDraft(rows=>rows.filter((_,n)=>n!==index))}><Trash2 size={16}/></button></div></section>})}</div><SaveBar dirty={JSON.stringify(draft)!==source} busy={busy} invalid={!draft.length||draft.some(row=>!row.name.trim()||!state.layouts.some(layout=>layout.hkl===row.hkl))} save={()=>void run('save_slots',{slots:draft})}/></>;
}
function Shortcuts({state,run,busy}:{state:Snapshot;run:Run;busy:boolean}) {
  const t=useT();const [draft,setDraft]=useState(state.shortcuts);const source=JSON.stringify(state.shortcuts);useEffect(()=>setDraft(state.shortcuts),[source]);
  const duplicate=(name:BindingName)=>Object.entries(state.shortcuts).some(([key,value])=>key!==name&&value.mode===draft[name].mode&&value.key===draft[name].key)||(state.features.tone&&draft[name].mode==='caps'&&'01234'.includes(draft[name].key));
  return <><Heading title={t('단축키')} description={t('기능별 사용 여부와 키 조합을 설정하세요.')}/>{(['selector','ja','zh','zh_tw'] as BindingName[]).map((name,index)=><section className="panel shortcut-editor" key={name}><div className="shortcut-title"><span className={`feature-symbol symbol-${index}`}>{['Aa','あ','简','繁'][index]}</span><h2>{t(names[name])}</h2><Toggle label={t(names[name])} checked={state.features[name]} disabled={busy} onChange={enabled=>void run('set_feature',{name,enabled})}/></div><div className="binding-fields"><Select label={`${t(names[name])} ${t('조합')}`} value={draft[name].mode} disabled={busy} onChange={mode=>setDraft({...draft,[name]:{...draft[name],mode}})}>{['caps','ctrl_shift','ctrl_alt'].map(mode=><option key={mode} value={mode}>{bindingLabel(mode)}</option>)}</Select><span>+</span><Select label={`${t(names[name])} ${t('키')}`} value={draft[name].key} disabled={busy} onChange={key=>setDraft({...draft,[name]:{...draft[name],key}})}>{[...'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',...Array.from({length:12},(_,n)=>`F${n+1}`)].map(key=><option key={key} value={key}>{key}</option>)}</Select><Button secondary disabled={busy||duplicate(name)||JSON.stringify(draft[name])===JSON.stringify(state.shortcuts[name])} onClick={()=>void run('set_shortcut',{name,...draft[name]})}>{t('적용')}</Button></div>{duplicate(name)&&<p className="field-error" role="alert">{t('이미 사용 중인 단축키입니다.')}</p>}</section>)}<section className="panel"><Setting label={t('병음 성조')} checked={state.features.tone} disabled={busy} change={enabled=>void run('set_feature',{name:'tone',enabled})}/><p className="muted">{t('병음 입력 후 Caps + 1~4로 성조 지정, Caps + 0으로 해제.')}</p></section>{state.language!=='ko'&&<p className="language-note">{t('발음 변환은 한국어 입력 기준입니다. 다른 키보드 환경에서는 지원하지 않을 수 있습니다.')}</p>}</>;
}
function Dictionary({state,run,busy}:{state:Snapshot;run:Run;busy:boolean}) {
  const t=useT();type Row=Entry&{id:string};const create=(entry:Entry):Row=>({...entry,id:crypto.randomUUID()});
  const [draft,setDraft]=useState<Row[]>(()=>state.dictionary.map(create));const source=JSON.stringify(state.dictionary);useEffect(()=>setDraft(state.dictionary.map(create)),[source]);
  const values=draft.map(({id:_,...entry})=>entry);const update=(id:string,patch:Partial<Entry>)=>setDraft(rows=>rows.map(row=>row.id===id?{...row,...patch}:row));
  const duplicate=draft.some((row,index)=>draft.some((other,n)=>index!==n&&row.keyword.trim()===other.keyword.trim()&&row.language===other.language));
  const add=()=>setDraft([...draft,create({keyword:'',text:'',language:'ja'})]);
  return <><Heading title={t('사용자 사전')} description={t('자주 쓰는 이름이나 표현을 원하는 표기로 등록하세요.')}/><div className="dictionary-example"><span>{t('예시')}</span><strong>도쿄</strong><span>→</span><strong lang="ja">東京</strong><small>{t('한일 변환')}</small></div><div className="section-title"><h2>{draft.length} / 1,000</h2><Button secondary disabled={busy||draft.length>=1000} onClick={add}><Plus size={16}/>{t('단어 추가')}</Button></div>{draft.length?<div className="dictionary-table panel"><div className="dictionary-labels"><span>{t('키워드')}</span><span>{t('대치할 텍스트')}</span><span>{t('언어')}</span><span/></div>{draft.map((row,index)=><div className="dictionary-row" key={row.id}><input aria-label={`${t('키워드')} ${index+1}`} placeholder={t('한글 발음')} maxLength={64} disabled={busy} value={row.keyword} onChange={event=>update(row.id,{keyword:event.target.value})}/><input aria-label={`${t('대치할 텍스트')} ${index+1}`} placeholder={t('대치할 텍스트')} maxLength={4096} disabled={busy} value={row.text} onChange={event=>update(row.id,{text:event.target.value})}/><Select label={`${t('언어')} ${index+1}`} value={row.language} disabled={busy} onChange={language=>update(row.id,{language})}>{[['ja','일본어'],['zh','중국어 간체'],['zh_tw','중국어 번체'],['zh_bopomofo','주음부호']].map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</Select><button className="icon-button" aria-label={`${t('단어 삭제')} ${index+1}`} disabled={busy} onClick={()=>setDraft(rows=>rows.filter(item=>item.id!==row.id))}><Trash2 size={17}/></button></div>)}</div>:<div className="empty-state panel"><BookOpen size={30}/><h2>{t('아직 등록된 단어가 없습니다.')}</h2><p>{t('발음과 표기를 한 번 등록하면 다음 입력부터 후보에 표시됩니다.')}</p><Button secondary onClick={add}>{t('단어 추가')}</Button></div>}{duplicate&&<p className="field-error" role="alert">{t('같은 언어에 동일한 키워드가 있습니다.')}</p>}<SaveBar dirty={JSON.stringify(values)!==source} busy={busy} invalid={duplicate||draft.some(row=>!row.keyword.trim()||!row.text.trim())} save={()=>void run('save_dictionary',{entries:values})}/></>;
}
