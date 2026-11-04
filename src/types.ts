export type Feature = 'selector' | 'ja' | 'zh' | 'zh_tw' | 'tone';
export type BindingName = Exclude<Feature, 'tone'>;
export type Binding = { mode: string; key: string };
export type Slot = { hkl: string; mode: string; name: string };
export type Entry = { keyword: string; text: string; language: string };
export type Layout = { hkl: string; name: string; tag: string; family: string; modes: {value: string; label: string}[] };
export type Snapshot = {
  version: string; connected: boolean; diagnostic: boolean; status: 'starting' | 'ready' | 'error'; error: string;
  enabled: boolean; running: boolean; firstRun: boolean; language: string;
  features: Record<Feature, boolean>; shortcuts: Record<BindingName, Binding>;
  slots: Slot[]; layouts: Layout[]; dictionary: Entry[];
  general: {showDashboard: boolean; startNotice: boolean; sound: boolean; autoStart: boolean; capsNotice:boolean};
  languages: {value: string; label: string}[]; translations: Record<string,string>;
};
export type Page = 'dashboard' | 'slots' | 'shortcuts' | 'dictionary' | 'settings' | 'about';
