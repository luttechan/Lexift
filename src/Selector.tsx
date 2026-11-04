import { useEffect, useLayoutEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { Check } from 'lucide-react';
import { host, native, preview } from './bridge';
import { useT } from './i18n';
import type { Slot } from './types';
type Frame={visible:boolean;revision:number;language:string;index:number;columns:number;page:string;shortcut:string;items:{slot:Slot;usable:boolean;key:string}[]};
const modeLabels: Record<string,string> = {
  ko_hangul: '한국어',
  ko_latin: '영어',
  ime_latin: '영어',
  ja_hiragana: '일본어 / 히라가나',
  ja_katakana_full: '가타카나 / 전각',
  ja_katakana_half: '가타카나 / 반각',
  ja_katakana_ask: '가타카나 / 매번 선택',
};
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
  return <div className="selector-shell"><header><div className="selector-mark"><img src="/lexift-icon.svg" width="32" height="32" alt="Lexift"/></div><div><h1>{t(frame.page==='width'?'가타카나 문자 폭':'언어 전환')}</h1><p>{t('숫자키 또는 방향키로 선택')}</p></div><kbd>{frame.shortcut}</kbd></header><div className="selector-grid" style={{gridTemplateColumns:`repeat(${frame.columns},minmax(0,1fr))`}}>{frame.items.map((item,index)=><button key={index} className={`selector-tile ${index===frame.index?'selected':''}`} disabled={!item.usable} aria-pressed={index===frame.index} onClick={()=>choose(index)}><div><kbd>{item.key}</kbd>{index===frame.index&&<Check size={17}/>}</div><strong>{item.slot.name}</strong><small>{t(modeLabels[item.slot.mode]||'현재 설정 유지')}</small></button>)}</div><footer><span><kbd>↵</kbd>{t('선택')}</span><span><kbd>Esc</kbd>{t('닫기')}</span><span>Lexift</span></footer></div>;
}
