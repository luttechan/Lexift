import { useEffect, useLayoutEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { Check, Globe2 } from 'lucide-react';
import { host, native, preview } from './bridge';
import { useT } from './i18n';
import type { Slot } from './types';
type Frame={visible:boolean;revision:number;language:string;index:number;columns:number;page:string;shortcut:string;items:{slot:Slot;usable:boolean;key:string}[]};
const demo:Frame={visible:true,revision:1,language:'ko',index:0,columns:3,page:'slots',shortcut:'Caps Lock + Q',items:[{slot:{hkl:'ko',mode:'ko_hangul',name:'한국어'},key:'1',usable:true},{slot:{hkl:'en',mode:'default',name:'English'},key:'2',usable:true},{slot:{hkl:'ja',mode:'ja_hiragana',name:'日本語'},key:'3',usable:true}]};
export function Selector({changeLocale}:{changeLocale:(language:string)=>void}) {
  const t=useT();const [frame,setFrame]=useState<Frame|null>(preview?demo:null);
  useEffect(()=>{
    let disposed=false;let unsubscribe:(()=>void)|undefined;
    if(native)void(async()=>{const cleanup=await listen<Frame>('engine-selector',event=>{if(!disposed)setFrame(event.payload)});if(disposed){cleanup();return}unsubscribe=cleanup;const current=await host('selector_snapshot') as Frame;if(!disposed)setFrame(current)})();
    return()=>{disposed=true;unsubscribe?.()};
  },[]);
  useEffect(()=>{if(frame?.language)changeLocale(frame.language)},[frame?.language,changeLocale]);
  useLayoutEffect(()=>{if(frame?.visible&&native)void host('selector_present',{revision:frame.revision}).catch(()=>{})},[frame?.revision,frame?.visible]);
  if(!frame?.visible)return <div className="selector-shell selector-empty"/>;
  const choose=(index:number)=>{if(native)void host('engine_command',{action:'selector_pick',payload:{index,revision:frame.revision}});else setFrame({...frame,index})};
  return <div className="selector-shell"><header><div className="selector-mark"><Globe2 size={21}/></div><div><h1>{t(frame.page==='width'?'가타카나 문자 폭':'언어 전환')}</h1><p>{t('숫자키 또는 방향키로 선택')}</p></div><kbd>{frame.shortcut}</kbd></header><div className="selector-grid" style={{gridTemplateColumns:`repeat(${frame.columns},minmax(0,1fr))`}}>{frame.items.map((item,index)=><button key={index} className={`selector-tile ${index===frame.index?'selected':''}`} disabled={!item.usable} aria-pressed={index===frame.index} onClick={()=>choose(index)}><div><kbd>{item.key}</kbd>{index===frame.index&&<Check size={17}/>}</div><strong>{item.slot.name}</strong><small>{item.slot.mode==='default'?'ABC':t(item.slot.mode.startsWith('ko_')?'한국어':item.slot.mode.startsWith('ja_')?'일본어':item.slot.mode.startsWith('zh_')?'중국어':'입력기')}</small></button>)}</div><footer><span><kbd>↵</kbd>{t('선택')}</span><span><kbd>Esc</kbd>{t('닫기')}</span><span>Lexift</span></footer></div>;
}
