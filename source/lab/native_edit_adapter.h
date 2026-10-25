// Standard Windows Edit/RichEdit compatibility without a UIA TextPattern.
// Edit uses system messages (< WM_USER), including marshalled WM_GETTEXT.
// Scintilla uses scalar-only messages. Never pass a remote custom pointer.
#pragma once
#include <windows.h>
#include <string>
#include <vector>
#include <algorithm>

struct NativeEditSnapshot {
    HWND target=nullptr, control=nullptr;
    std::wstring token, key;
    std::wstring fullText;
    DWORD documentLength=0;
    DWORD start=0, end=0;
    bool scintilla=false;
    RECT caret={};
};
static bool inlineCommitSpace=false;
static bool inlineRoman=false;
static bool editMessage(HWND control,UINT message,WPARAM w,LPARAM l,DWORD_PTR& answer) {
    return SendMessageTimeoutW(control,message,w,l,SMTO_ABORTIFHUNG|SMTO_BLOCK,120,&answer)!=0;
}
static bool nativeEditClass(HWND control) {
    if(!IsWindowUnicode(control)) return false;
    wchar_t name[128]={};GetClassNameW(control,name,128);
    return !_wcsicmp(name,L"Edit") || !_wcsicmp(name,L"RichEdit20W") ||
           !_wcsicmp(name,L"RICHEDIT50W") || !_wcsicmp(name,L"RichEditD2DPT");
}
static bool nativeHangul(wchar_t c) {
    if(inlineRoman)return (c>=L'a' && c<=L'z') || (c>=L'A' && c<=L'Z') || c==L':' || (c>=0xc0 && c<=0x24f) || (c>=0x300 && c<=0x36f) || (c>=0x1e00 && c<=0x1eff);
    return (c>=0xac00 && c<=0xd7a3) || (c>=0x3131 && c<=0x3163) ||
           (c>=0x1100 && c<=0x11ff) || c==L'-' || c==L'ー';
}
#include "scintilla_adapter.h"
static bool readNativeEdit(HWND target,HWND control,NativeEditSnapshot& result) {
    if(!control || !target || GetAncestor(control,GA_ROOT)!=target || !IsWindowEnabled(control))return false;
    wchar_t name[128]={};GetClassNameW(control,name,128);
    if(!_wcsicmp(name,L"Scintilla"))return readScintilla(target,control,result);
    if(!nativeEditClass(control))return false;
    LONG_PTR style=GetWindowLongPtrW(control,GWL_STYLE);
    if(style&(ES_PASSWORD|ES_READONLY)) return false;
    DWORD_PTR password=0;
    if(!editMessage(control,EM_GETPASSWORDCHAR,0,0,password) || password) return false;
    DWORD_PTR length=0,selection=0,after=0,copied=0;
    if(!editMessage(control,WM_GETTEXTLENGTH,0,0,length) || !length || length>60000) return false;
    if(!editMessage(control,EM_GETSEL,0,0,selection) || selection==0xffffffff) return false;
    DWORD start=LOWORD(selection),end=HIWORD(selection);
    if(start!=end || end>length) return false;
    std::vector<wchar_t> buffer((size_t)length+1,0);
    if(!editMessage(control,WM_GETTEXT,buffer.size(),(LPARAM)buffer.data(),copied) || copied!=length) return false;
    if(!editMessage(control,EM_GETSEL,0,0,after) || after!=selection) return false;
    std::wstring text(buffer.data(),(size_t)copied);
    // RichEdit WM_GETTEXT can expand paragraph marks to CRLF while EM_GETSEL
    // counts CR only. Refuse offset ambiguity instead of selecting wrong text.
    // UIA remains the primary route for multiline RichEdit documents.
    wchar_t className[128]={};GetClassNameW(control,className,128);
    if(_wcsicmp(className,L"Edit") && text.find(L'\n')!=std::wstring::npos) return false;
    size_t begin=end;
    if(inlineCommitSpace && begin && text[begin-1]==L' ')--begin;
    while(begin && nativeHangul(text[begin-1])) --begin;
    if(begin==end || end-begin>200+(inlineCommitSpace?1:0)) return false;
    result.target=target;result.control=control;result.start=(DWORD)begin;result.end=end;
    result.token=text.substr(begin,end-begin);
    result.fullText=text;result.documentLength=(DWORD)length;
    result.key=L"native:"+std::to_wstring((ULONG_PTR)target)+L":"+
        std::to_wstring((ULONG_PTR)control)+L":"+std::to_wstring(end)+L"|"+text;
    return true;
}
static bool sameNativeEdit(const NativeEditSnapshot& a,const NativeEditSnapshot& b) {
    return a.target==b.target && a.control==b.control && a.start==b.start &&
           a.end==b.end && a.token==b.token && a.key==b.key;
}
static bool sameNativeAfterCommitSpace(const NativeEditSnapshot& a,const NativeEditSnapshot& b) {
    if(a.target!=b.target || a.control!=b.control || a.scintilla!=b.scintilla || a.start!=b.start ||
       b.end!=a.end+1 || b.documentLength!=a.documentLength+1 || b.token!=a.token+L" ")return false;
    if(a.scintilla)return true;
    auto expected=a.fullText;expected.insert(a.end,L" ");return b.fullText==expected;
}
static bool selectNativeEdit(const NativeEditSnapshot& expected) {
    NativeEditSnapshot fresh;
    if(!readNativeEdit(expected.target,expected.control,fresh) || !sameNativeEdit(expected,fresh)) return false;
    DWORD_PTR answer=0,selection=0;
    if(expected.scintilla) {
        DWORD_PTR anchor=0;
        return editMessage(expected.control,2160,expected.start,expected.end,answer) &&
            editMessage(expected.control,2009,0,0,anchor) && anchor==expected.start &&
            editMessage(expected.control,2008,0,0,selection) && selection==expected.end;
    }
    if(!editMessage(expected.control,EM_SETSEL,expected.start,expected.end,answer)) return false;
    return editMessage(expected.control,EM_GETSEL,0,0,selection) &&
           LOWORD(selection)==expected.start && HIWORD(selection)==expected.end;
}
