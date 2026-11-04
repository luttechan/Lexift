import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { host, native, preview } from './bridge';

type PopupFrame = {
  visible: boolean;
  revision: number;
  source?: string;
  values?: string[];
  readings?: string[];
  row?: number;
  hint?: string;
  title?: string;
  text?: string;
  kind?: string;
};

const sample: PopupFrame = {
  visible: true, revision: 1, source: '와타시', values: ['私','わたし','ワタシ','わたくし'], // i18n-sample
  readings: ['わたし','わたし','ワタシ','わたくし'], row: 0, hint: '1–9 / 0 확정 / ↑↓ 이동 / Space / Enter',
};

export function Popup({candidate}:{candidate:boolean}) {
  const [frame,setFrame]=useState<PopupFrame|null>(preview&&candidate?sample:null);
  const selected=useRef<HTMLButtonElement>(null);
  useEffect(()=>{
    let disposed=false;
    let cleanup:(()=>void)|undefined;
    if(native)void(async()=>{
      const unlisten=await listen<PopupFrame>('engine-popup',event=>{if(!disposed)setFrame(event.payload)});
      if(disposed){unlisten();return;}
      cleanup=unlisten;
      const snapshot=await host('popup_snapshot') as PopupFrame;
      if(!disposed)setFrame(current=>current && current.revision>(snapshot.revision||0)?current:snapshot);
    })().catch(()=>{});
    return()=>{disposed=true;cleanup?.()};
  },[]);

  useLayoutEffect(()=>{
    if(frame?.visible&&native)void host('popup_present',{revision:frame.revision}).catch(()=>{});
  },[frame?.visible,frame?.revision]);
  useLayoutEffect(()=>{selected.current?.scrollIntoView({block:'nearest'})},[frame?.row,frame?.revision]);

  if(!frame?.visible)return null;
  if(!candidate){
    const content=<>{frame.title&&<strong>{frame.title}</strong>}<span>{frame.text}</span></>;
    return frame.kind==='notification'?
      <button className="notice-popup" onClick={()=>void host('engine_command',{action:'tray_action',payload:{name:'main'}}).catch(()=>{})}>{content}</button>:
      <div className="notice-popup" role="status">{content}</div>;
  }

  return <section className="candidate-popup" aria-label="Lexift">
    <header>
      <span className="candidate-brand">LEXIFT</span>
      <div className="candidate-reading" title={frame.source}>{frame.source} <span>→</span> {frame.readings?.[frame.row??0]}</div>
    </header>
    <div className="candidate-list" role="listbox">
      {frame.values?.map((value,index)=><button
        className="candidate-row"
        key={index}
        role="option"
        aria-selected={index===frame.row}
        ref={index===frame.row?selected:undefined}
        title={value}
        onMouseDown={event=>event.preventDefault()}
        onClick={()=>{
          if(native)void host('engine_command',{action:'candidate_pick',payload:{row:index,revision:frame.revision}}).catch(()=>{});
          else setFrame({...frame,row:index});
        }}>
        <kbd>{index===9?'0':index+1}</kbd><span>{value}</span>
      </button>)}
    </div>
    <footer>{frame.hint}</footer>
  </section>;
}
