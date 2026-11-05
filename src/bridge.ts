import { invoke, isTauri } from '@tauri-apps/api/core';
import type { Snapshot } from './types';

export const native = isTauri();
export const preview = !native && new URLSearchParams(location.search).has('preview');
const seed: Snapshot = {
  version: '1.2.1', connected: false, diagnostic: true, status: 'ready', error: '', enabled: true, running: false, firstRun: false, language: 'ko',
  features: {selector:true,ja:true,zh:true,zh_tw:true,tone:false},
  shortcuts: {selector:{mode:'caps',key:'Q'},ja:{mode:'caps',key:'A'},zh:{mode:'caps',key:'C'},zh_tw:{mode:'caps',key:'T'}},
  slots: [{hkl:'ko',mode:'ko_hangul',name:'한국어'},{hkl:'en',mode:'default',name:'English'},{hkl:'ja',mode:'ja_hiragana',name:'日本語'}],
  layouts: [{hkl:'ko',name:'한국어',tag:'ko-KR',family:'korean',modes:[{value:'ko_hangul',label:'한국어'},{value:'ko_latin',label:'영어'}]},{hkl:'en',name:'English',tag:'en-US',family:'standard',modes:[{value:'default',label:'기본'}]},{hkl:'ja',name:'日本語',tag:'ja-JP',family:'japanese',modes:[{value:'ja_hiragana',label:'히라가나'},{value:'ja_katakana_full',label:'가타카나'}]}],
  dictionary: [], general: {showDashboard:true,startNotice:true,sound:true,autoStart:false,capsNotice:true}, languages:[{value:'ko',label:'한국어'},{value:'en',label:'English'},{value:'ja',label:'日本語'},{value:'zh_CN',label:'简体中文'},{value:'zh_TW',label:'繁體中文'},{value:'fr',label:'Français'},{value:'es',label:'Español'},{value:'ru',label:'Русский'},{value:'de',label:'Deutsch'}],translations:{},
};
let memory = structuredClone(seed);

export async function command(action: string, payload: Record<string,unknown> = {}): Promise<Snapshot> {
  if (native) return invoke<Snapshot>('engine_command', {action,payload});
  if (!preview) throw new Error('Lexift 데스크톱 앱에서 실행하세요.');
  // Explicit browser preview: no writes to the real application's settings.
  if (action === 'set_enabled') memory.enabled = Boolean(payload.enabled);
  if (action === 'set_feature') memory.features[payload.name as keyof typeof memory.features] = Boolean(payload.enabled);
  if (action === 'set_shortcut') memory.shortcuts[payload.name as keyof typeof memory.shortcuts] = {mode:String(payload.mode),key:String(payload.key)};
  if (action === 'save_slots') memory.slots = structuredClone(payload.slots) as Snapshot['slots'];
  if (action === 'save_dictionary') memory.dictionary = structuredClone(payload.entries) as Snapshot['dictionary'];
  if (action === 'set_general') { const {language,...general} = payload; memory.general = {...memory.general,...general}; if (language) memory.language = String(language); }
  if (action === 'reset_defaults') memory = structuredClone(seed);
  return structuredClone(memory);
}

export async function host(action: string, payload: Record<string,unknown> = {}) { if (native) return invoke(action,payload); }
export function bindingLabel(mode: string) { return ({caps:'Caps Lock',ctrl_shift:'Ctrl + Shift',ctrl_alt:'Ctrl + Alt'} as Record<string,string>)[mode] || mode; }
