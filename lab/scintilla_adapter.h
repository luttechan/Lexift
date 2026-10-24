// Scintilla fallback uses scalar-only messages: no remote process pointers.
#pragma once
static bool scintillaMessage(HWND control,UINT message,WPARAM w,LPARAM l,DWORD_PTR& value) {
    return editMessage(control,message,w,l,value);
}
static bool readScintilla(HWND target,HWND control,NativeEditSnapshot& result) {
    DWORD_PTR codepage=0,readonly=1,selections=0,anchor=0,position=0,length=0,rectangle=1,virtualSpace=1;
    if(!scintillaMessage(control,2137,0,0,codepage)||codepage!=65001 ||
       !scintillaMessage(control,2140,0,0,readonly)||readonly ||
       !scintillaMessage(control,2570,0,0,selections)||selections!=1 ||
       !scintillaMessage(control,2372,0,0,rectangle)||rectangle ||
       !scintillaMessage(control,2581,0,0,virtualSpace)||virtualSpace ||
       !scintillaMessage(control,2009,0,0,anchor) ||
       !scintillaMessage(control,2008,0,0,position)||anchor!=position ||
       !scintillaMessage(control,2006,0,0,length)||position>length || length>0x7fffffff) return false;
    DWORD_PTR begin=position;std::wstring token;ULONGLONG started=GetTickCount64();
    while(begin && token.size()<=200) {
        if(GetTickCount64()-started>40)return false;
        DWORD_PTR previous=0;
        if(!scintillaMessage(control,2417,begin,0,previous)||previous>=begin||begin-previous>4)return false;
        std::string encoded;
        for(DWORD_PTR p=previous;p<begin;p++) {
            DWORD_PTR byte=0;if(!scintillaMessage(control,2007,p,0,byte))return false;
            encoded.push_back((char)(byte&255));
        }
        wchar_t decoded[2]={};int units=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,encoded.data(),(int)encoded.size(),decoded,2);
        if(units!=1 || (!nativeHangul(decoded[0]) && !(inlineCommitSpace && token.empty() && decoded[0]==L' ')))break;
        token.insert(token.begin(),decoded[0]);begin=previous;
    }
    if(token.empty()||token.size()>200+(inlineCommitSpace?1:0))return false;
    DWORD_PTR after=0,afterAnchor=0,afterLength=0;
    if(!scintillaMessage(control,2008,0,0,after)||after!=position ||
       !scintillaMessage(control,2009,0,0,afterAnchor)||afterAnchor!=position ||
       !scintillaMessage(control,2006,0,0,afterLength)||afterLength!=length)return false;
    DWORD_PTR x=0,y=0,line=0,height=0;
    if(!scintillaMessage(control,2164,0,position,x)||!scintillaMessage(control,2165,0,position,y)||
       !scintillaMessage(control,2166,position,0,line)||!scintillaMessage(control,2279,line,0,height))return false;
    LONG px=(LONG)x,py=(LONG)y;
    RECT client={};GetClientRect(control,&client);
    if(px<0||py<0||px>client.right||py>client.bottom||height==0||height>1000)return false;
    POINT point={px,py+(LONG)height};if(!ClientToScreen(control,&point))return false;
    result.scintilla=true;result.target=target;result.control=control;
    result.start=(DWORD)begin;result.end=(DWORD)position;result.token=token;
    result.documentLength=(DWORD)length;
    result.caret={point.x,point.y,point.x,point.y};
    result.key=L"scintilla:"+std::to_wstring((ULONG_PTR)target)+L":"+std::to_wstring((ULONG_PTR)control)+L":"+
        std::to_wstring(position)+L":"+std::to_wstring(length)+L"|"+token;
    return true;
}
