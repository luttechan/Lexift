import { createContext, useContext, type ReactNode } from 'react';
import catalog from './locales.json';
const Locale=createContext('ko');
export function I18n({language,children}:{language:string;children:ReactNode}) {return <Locale.Provider value={language}>{children}</Locale.Provider>}
export function useT() {
  const language=useContext(Locale);
  return (key:string,values:Record<string,string|number>={})=>{
    let text=(catalog as Record<string,Record<string,string>>)[language]?.[key]||key;
    for(const [name,value] of Object.entries(values))text=text.replaceAll(`{${name}}`,String(value));
    return text;
  };
}
