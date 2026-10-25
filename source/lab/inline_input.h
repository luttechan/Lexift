// UI Automation works across process boundaries without injecting a text service.
#include <uiautomation.h>
#include <oleacc.h>
#include <algorithm>
#include <deque>
#include <memory>
#include "native_edit_adapter.h"
#include "ia2_adapter.h"
static DWORD inlineOwnerPid=0;

struct InlineSnapshot {
    HWND target=nullptr;
    std::wstring token,key,contextKey;
    std::wstring prefix;
    RECT caret={};
    IUIAutomationTextRange* range=nullptr;
    IUIAutomationElement* element=nullptr;
    int reason=0;
    bool blocked=false, native=false, nativeTextValid=false;
    const char* backend="uia-text";
    NativeEditSnapshot edit;
    std::shared_ptr<Ia2Snapshot> ia2;
    ~InlineSnapshot() {if(range) range->Release();if(element)element->Release();}
};
static bool hangulCharacter(wchar_t c) {
    if(inlineRoman)return nativeHangul(c);
    return (c>=0xac00 && c<=0xd7a3) || (c>=0x3131 && c<=0x3163) ||
        (c>=0x1100 && c<=0x11ff) || c==L'-' || c==L'ー';
}
static bool uiaInlineSnapshot(IUIAutomation* automation,InlineSnapshot& result) {
    result.target=GetForegroundWindow();
    DWORD pid=0;GetWindowThreadProcessId(result.target,&pid);
    if(!pid || pid==GetCurrentProcessId() || pid==inlineOwnerPid) {result.reason=1;return false;}
    IUIAutomationElement* element=nullptr;
    if(FAILED(automation->GetFocusedElement(&element)) || !element) {result.reason=2;return false;}
    int focusedPid=0;element->get_CurrentProcessId(&focusedPid);
    if((DWORD)focusedPid!=pid) {
        // Browser renderers can expose the edit from a different process.
        // Verify UIA ancestry instead of rejecting every such input field.
        IUIAutomationTreeWalker* walker=nullptr;automation->get_RawViewWalker(&walker);
        IUIAutomationElement* ancestor=element;ancestor->AddRef();bool belongs=false;
        for(int depth=0;walker && ancestor && depth<32;depth++) {
            UIA_HWND native=nullptr;ancestor->get_CurrentNativeWindowHandle(&native);
            if((HWND)native==result.target) {belongs=true;break;}
            IUIAutomationElement* parent=nullptr;walker->GetParentElement(ancestor,&parent);
            ancestor->Release();ancestor=parent;
        }
        if(ancestor) ancestor->Release();if(walker) walker->Release();
        if(!belongs) {element->Release();result.reason=11;return false;}
    }
    std::wstring identity;
    SAFEARRAY* runtime=nullptr;
    if(SUCCEEDED(element->GetRuntimeId(&runtime)) && runtime) {
        LONG low=0,high=-1;SafeArrayGetLBound(runtime,1,&low);SafeArrayGetUBound(runtime,1,&high);
        if(high-low<100) for(LONG i=low;i<=high;i++) {
            int value=0;SafeArrayGetElement(runtime,&i,&value);identity+=L":"+std::to_wstring(value);
        }
        SafeArrayDestroy(runtime);
    }
    BOOL password=TRUE,enabled=FALSE;
    element->get_CurrentIsPassword(&password);element->get_CurrentIsEnabled(&enabled);
    CONTROLTYPEID type=0;element->get_CurrentControlType(&type);
    if(password || !enabled) {result.blocked=true;element->Release();result.reason=type;return false;}
    IUIAutomationTextPattern* pattern=nullptr;
    HRESULT hr=element->GetCurrentPatternAs(UIA_TextPatternId,__uuidof(IUIAutomationTextPattern),(void**)&pattern);
    IUIAutomationTextPattern2* caretPattern=nullptr;
    element->GetCurrentPatternAs(UIA_TextPattern2Id,__uuidof(IUIAutomationTextPattern2),(void**)&caretPattern);
    result.element=element;
    if((FAILED(hr) || !pattern) && caretPattern) {
        caretPattern->QueryInterface(__uuidof(IUIAutomationTextPattern),(void**)&pattern);
    }
    if(!pattern) {if(caretPattern)caretPattern->Release();result.reason=3;return false;}
    IUIAutomationTextRangeArray* array=nullptr;
    pattern->GetSelection(&array);pattern->Release();
    int count=0;if(array)array->get_Length(&count);
    IUIAutomationTextRange* caret=nullptr;
    if(count==1) array->GetElement(0,&caret);
    if(array) array->Release();
    // TextPattern2 can expose an active caret where GetSelection gives no
    // range. Never turn a nonempty/multiple selection into a caret query.
    if(!caret && count==0 && caretPattern) {
        BOOL active=FALSE;
        if(SUCCEEDED(caretPattern->GetCaretRange(&active,&caret)) && active && caret)
            result.backend="uia-caret";
        else if(caret) {caret->Release();caret=nullptr;}
    }
    if(caretPattern)caretPattern->Release();
    if(!caret) {result.reason=5;return false;}
    BSTR selected=nullptr;caret->GetText(1,&selected);
    bool collapsed=!selected || SysStringLen(selected)==0;SysFreeString(selected);
    if(!collapsed) {caret->Release();result.reason=6;return false;}
    VARIANT readOnly;VariantInit(&readOnly);
    caret->GetAttributeValue(UIA_IsReadOnlyAttributeId,&readOnly);
    bool editable=readOnly.vt==VT_BOOL && readOnly.boolVal==VARIANT_FALSE;
    bool locked=(readOnly.vt==VT_BOOL && readOnly.boolVal==VARIANT_TRUE) ||
        ((type!=UIA_EditControlTypeId && type!=UIA_DocumentControlTypeId) && !editable);
    VariantClear(&readOnly);
    if(locked) {result.blocked=true;caret->Release();result.reason=7;return false;}
    IUIAutomationTextRange* preceding=nullptr;caret->Clone(&preceding);
    if(!preceding) {caret->Release();result.reason=8;return false;}
    int moved=0;preceding->MoveEndpointByUnit(TextPatternRangeEndpoint_Start,TextUnit_Character,-256,&moved);
    BSTR content=nullptr;preceding->GetText(1024,&content);
    std::wstring prefix=content?std::wstring(content,SysStringLen(content)):L"";
    SysFreeString(content);preceding->Release();
    size_t start=prefix.size();
    if(inlineCommitSpace && start && prefix[start-1]==L' ')--start;
    while(start && hangulCharacter(prefix[start-1])) start--;
    result.token=prefix.substr(start);
    result.prefix=prefix;
    if(result.token.empty() || result.token.size()>200+(inlineCommitSpace?1:0)) {caret->Release();result.reason=9;return false;}
    result.range=caret;
    caret->MoveEndpointByUnit(TextPatternRangeEndpoint_Start,TextUnit_Character,-(int)result.token.size(),&moved);
    BSTR verify=nullptr;caret->GetText(256,&verify);
    std::wstring actual=verify?std::wstring(verify,SysStringLen(verify)):L"";SysFreeString(verify);
    if(actual!=result.token) {result.reason=10;return false;}
    bool positioned=false;
    SAFEARRAY* bounds=nullptr;caret->GetBoundingRectangles(&bounds);
    if(bounds) {
        LONG low=0,high=-1;SafeArrayGetLBound(bounds,1,&low);SafeArrayGetUBound(bounds,1,&high);
        if(high-low>=3) {
            double* values=nullptr;
            if(SUCCEEDED(SafeArrayAccessData(bounds,(void**)&values))) {
                int index=((high-low+1)/4-1)*4;
                result.caret={(LONG)(values[index]+values[index+2]),(LONG)values[index+1],(LONG)(values[index]+values[index+2]),(LONG)(values[index+1]+values[index+3])};
                positioned=values[index+3]>0;
                SafeArrayUnaccessData(bounds);
            }
        }
        SafeArrayDestroy(bounds);
    }
    if(!positioned) {
        GUITHREADINFO info={sizeof info};
        if(GetGUIThreadInfo(0,&info) && info.hwndCaret) {
            POINT point={info.rcCaret.left,info.rcCaret.bottom};
            if(ClientToScreen(info.hwndCaret,&point) && info.rcCaret.bottom>info.rcCaret.top) {
                result.caret={point.x,point.y-20,point.x,point.y};positioned=true;
            }
        }
    }
    if(!positioned) {
        IAccessible* accessible=nullptr;
        if(SUCCEEDED(AccessibleObjectFromWindow(result.target,OBJID_CARET,IID_IAccessible,(void**)&accessible)) && accessible) {
            VARIANT child;VariantInit(&child);child.vt=VT_I4;child.lVal=CHILDID_SELF;
            LONG x=0,y=0,width=0,height=0;
            if(SUCCEEDED(accessible->accLocation(&x,&y,&width,&height,child)) && height>0) {
                result.caret={x,y,x+width,y+height};positioned=true;
            }
            accessible->Release();
        }
    }
    if(!positioned) {
        // Some editable providers expose text but no caret geometry. Keep the
        // valid candidate available directly below the focused input control.
        RECT field={};
        if(SUCCEEDED(element->get_CurrentBoundingRectangle(&field)) && field.right>field.left && field.bottom>field.top) {
            result.caret={field.left+8,field.top,field.left+8,std::min(field.bottom,field.top+24)};positioned=true;
        }
    }
    // Compare the surrounding text and position again before replacement.
    result.contextKey=std::to_wstring((ULONG_PTR)result.target)+identity+L"|"+prefix;
    result.key=result.contextKey+L"|"+std::to_wstring(result.caret.left)+L","+std::to_wstring(result.caret.bottom);
    if(!positioned) {result.reason=12;return false;}
    return true;
}
static bool nativeInlineSnapshot(IUIAutomation* automation,InlineSnapshot& result) {
    GUITHREADINFO info={sizeof info};
    if(!GetGUIThreadInfo(0,&info) || !info.hwndFocus || GetForegroundWindow()!=result.target) return false;
    NativeEditSnapshot edit;
    if(!readNativeEdit(result.target,info.hwndFocus,edit)) return false;
    result.nativeTextValid=true;
    if(GetForegroundWindow()!=edit.target) return false;
    bool positioned=edit.scintilla;
    if(!edit.scintilla && info.hwndCaret) {
        POINT point={info.rcCaret.left,info.rcCaret.bottom};
        if(info.rcCaret.bottom>info.rcCaret.top && ClientToScreen(info.hwndCaret,&point)) {
            edit.caret={point.x,point.y-20,point.x,point.y};positioned=true;
        }
    }
    bool fieldAnchor=false;
    if(!positioned && uiaInlineSnapshot(automation,result))return true;
    if(!positioned) {
        wchar_t name[128]={};GetClassNameW(edit.control,name,128);
        if(!_wcsicmp(name,L"Edit")) {
            DWORD_PTR packed=0;bool previous=false;
            bool located=editMessage(edit.control,EM_POSFROMCHAR,edit.end,0,packed) && (LONG)packed!=-1;
            if(!located && edit.end) {
                located=editMessage(edit.control,EM_POSFROMCHAR,edit.end-1,0,packed) && (LONG)packed!=-1;previous=true;
            }
            if(located) {
                TEXTMETRICW metrics={};SIZE advance={};HDC dc=GetDC(edit.control);DWORD_PTR font=0;
                HGDIOBJ old=nullptr;
                if(dc && editMessage(edit.control,WM_GETFONT,0,0,font) && font)old=SelectObject(dc,(HFONT)font);
                if(dc) {
                    GetTextMetricsW(dc,&metrics);
                    if(previous && !edit.token.empty())GetTextExtentPoint32W(dc,&edit.token.back(),1,&advance);
                    if(old)SelectObject(dc,old);ReleaseDC(edit.control,dc);
                }
                POINT point={(SHORT)LOWORD(packed)+advance.cx,(SHORT)HIWORD(packed)};
                if(ClientToScreen(edit.control,&point)) {
                    LONG height=metrics.tmHeight>0?metrics.tmHeight:20;
                    edit.caret={point.x,point.y,point.x,point.y+height};positioned=true;
                }
            }
        }
    }
    if(!positioned) {
        RECT field={};
        if(GetWindowRect(edit.control,&field) && field.right>field.left && field.bottom>field.top) {
            edit.caret={field.left+8,field.top,field.left+8,std::min(field.bottom,field.top+24)};positioned=true;fieldAnchor=true;
        }
    }
    if(!positioned)return false;
    result.native=true;result.backend=edit.scintilla?"scintilla-utf8":fieldAnchor?"win32-edit-field":"win32-edit";result.reason=0;
    result.edit=edit;result.token=edit.token;result.key=edit.key+L"|"+
        std::to_wstring(edit.caret.left)+L","+std::to_wstring(edit.caret.bottom);
    result.caret=edit.caret;return true;
}
static bool ia2InlineSnapshot(InlineSnapshot& result) {
    IAccessible* focused=focusedMsaa(result.target);
    if(!focused)return false;
    auto snapshot=std::make_shared<Ia2Snapshot>();
    bool valid=readIa2Object(focused,*snapshot);focused->Release();
    if(snapshot->blocked)result.blocked=true;
    if(!valid)return false;
    if(GetForegroundWindow()!=result.target)return false;
    result.ia2=snapshot;result.token=snapshot->token;result.caret=snapshot->caret;
    result.backend="msaa-ia2";result.reason=0;
    result.contextKey=L"ia2:"+std::to_wstring((ULONG_PTR)result.target)+L":"+
        std::to_wstring((ULONG_PTR)snapshot->identity)+L":"+std::to_wstring(snapshot->end)+L":"+
        std::to_wstring(snapshot->length)+L"|"+snapshot->before+L"|"+snapshot->after;
    result.key=result.contextKey+L"|"+std::to_wstring(result.caret.left)+L","+std::to_wstring(result.caret.bottom);
    return true;
}
static bool inlineSnapshot(IUIAutomation* automation,InlineSnapshot& result) {
    result.target=GetForegroundWindow();DWORD pid=0;
    GetWindowThreadProcessId(result.target,&pid);
    if(!pid || pid==GetCurrentProcessId() || pid==inlineOwnerPid) {result.reason=1;return false;}
    // Standard native controls expose authoritative password/read-only/selection
    // state directly. Avoid repeated cross-process COM round trips for them.
    if(nativeInlineSnapshot(automation,result))return true;
    GUITHREADINFO info={sizeof info};
    if(GetGUIThreadInfo(0,&info) && info.hwndFocus && GetAncestor(info.hwndFocus,GA_ROOT)==result.target) {
        wchar_t name[128]={};GetClassNameW(info.hwndFocus,name,128);
        if(!result.nativeTextValid && !_wcsicmp(name,L"Edit") && IsWindowUnicode(info.hwndFocus)) {
            DWORD_PTR length=0;
            if(!editMessage(info.hwndFocus,WM_GETTEXTLENGTH,0,0,length) || length<=60000) {
                result.reason=14;return false; // native path already checked this control
            }
        }
    }
    wchar_t windowClass[128]={};GetClassNameW(result.target,windowClass,128);
    bool gecko=!_wcsicmp(windowClass,L"MozillaWindowClass");
    if(gecko && ia2InlineSnapshot(result))return true;
    if(result.blocked)return false;
    if(uiaInlineSnapshot(automation,result))return true;
    if(result.blocked)return false;
    if(!gecko && ia2InlineSnapshot(result))return true;
    return false;
}
static bool prepareInlineReplacement(IUIAutomation* automation,const InlineSnapshot& snapshot) {
    if(GetForegroundWindow()!=snapshot.target) return false;
    if(snapshot.ia2) {
        IAccessible* focused=focusedMsaa(snapshot.target);if(!focused)return false;
        bool valid=prepareIa2Replacement(focused,*snapshot.ia2);
        focused->Release();return valid;
    }
    if(snapshot.native) {
        GUITHREADINFO info={sizeof info};
        if(!GetGUIThreadInfo(0,&info) || info.hwndFocus!=snapshot.edit.control || !selectNativeEdit(snapshot.edit))return false;
        return GetGUIThreadInfo(0,&info) && info.hwndFocus==snapshot.edit.control;
    }
    if(!snapshot.range || !snapshot.element || FAILED(snapshot.range->Select()))return false;
    IUIAutomationElement* focused=nullptr;BOOL same=FALSE;
    if(SUCCEEDED(automation->GetFocusedElement(&focused)) && focused) {
        automation->CompareElements(snapshot.element,focused,&same);focused->Release();
    }
    return same;
}
static bool sameInlineLocation(IUIAutomation* automation,const InlineSnapshot& a,const InlineSnapshot& b) {
    if(a.target!=b.target || a.native!=b.native || a.token!=b.token)return false;
    if(a.ia2 || b.ia2)return a.ia2 && b.ia2 && sameIa2(*a.ia2,*b.ia2);
    if(a.native)return sameNativeEdit(a.edit,b.edit);
    if(a.contextKey!=b.contextKey || !a.range || !b.range || !a.element || !b.element)return false;
    BOOL same=FALSE;
    if(FAILED(automation->CompareElements(a.element,b.element,&same)) || !same)return false;
    int start=1,end=1;
    return SUCCEEDED(a.range->CompareEndpoints(TextPatternRangeEndpoint_Start,b.range,TextPatternRangeEndpoint_Start,&start)) &&
        SUCCEEDED(a.range->CompareEndpoints(TextPatternRangeEndpoint_End,b.range,TextPatternRangeEndpoint_End,&end)) && start==0 && end==0;
}
static bool sameAfterCommitSpace(IUIAutomation* automation,const InlineSnapshot& before,const InlineSnapshot& after) {
    if(before.target!=after.target || before.native!=after.native || after.token!=before.token+L" ")return false;
    if(before.native)return sameNativeAfterCommitSpace(before.edit,after.edit);
    if(before.ia2 || after.ia2)return before.ia2 && after.ia2 && sameIa2AfterCommitSpace(*before.ia2,*after.ia2);
    if(!before.element || !after.element || !before.range || !after.range)return false;
    BOOL same=FALSE;int start=1;
    if(FAILED(automation->CompareElements(before.element,after.element,&same)) || !same)return false;
    auto suffix=before.prefix.substr(before.prefix.size()>128?before.prefix.size()-128:0)+L" ";
    return after.prefix.size()>=suffix.size() && after.prefix.compare(after.prefix.size()-suffix.size(),suffix.size(),suffix)==0 &&
        SUCCEEDED(before.range->CompareEndpoints(TextPatternRangeEndpoint_Start,after.range,TextPatternRangeEndpoint_Start,&start)) && start==0;
}
struct CommitSpaceScope {
    CommitSpaceScope(){inlineCommitSpace=true;}
    ~CommitSpaceScope(){inlineCommitSpace=false;}
};
static bool refreshInlineSnapshot(IUIAutomation* automation,const InlineSnapshot& before,InlineSnapshot& after) {
    after.target=GetForegroundWindow();if(after.target!=before.target)return false;
    if(before.native)return nativeInlineSnapshot(automation,after);
    if(before.ia2)return ia2InlineSnapshot(after);
    return uiaInlineSnapshot(automation,after);
}
static std::shared_ptr<InlineSnapshot> settleInlineComposition(IUIAutomation* automation,const InlineSnapshot& before) {
    // A foreign process does not own this app's HIMC/TSF composition. Let its
    // real Korean IME commit naturally, then remove exactly this added space
    // together with the verified original reading. No caret movement keys.
    if(GetForegroundWindow()!=before.target)return {};
    INPUT keys[2]={};keys[0].type=keys[1].type=INPUT_KEYBOARD;
    keys[0].ki.wVk=keys[1].ki.wVk=VK_SPACE;keys[1].ki.dwFlags=KEYEVENTF_KEYUP;
    if(SendInput(2,keys,sizeof(INPUT))!=2)return {};
    ULONGLONG deadline=GetTickCount64()+180;
    while(GetTickCount64()<deadline) {
        if(GetForegroundWindow()!=before.target)return {};
        auto after=std::make_shared<InlineSnapshot>();
        if(refreshInlineSnapshot(automation,before,*after) && sameAfterCommitSpace(automation,before,*after))return after;
        Sleep(5);
    }
    return {};
}
static std::wstring fromHex(const std::string& text) {
    std::wstring result;
    if(text.size()%4 || text.size()>4096) return result;
    for(size_t i=0;i<text.size();i+=4) {
        unsigned value=0;
        for(size_t j=0;j<4;j++) {
            char c=text[i+j];int digit=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;
            if(digit<0) return L"";
            value=value*16+digit;
        }
        result.push_back((wchar_t)value);
    }
    return result;
}
static void CALLBACK inlineChanged(HWINEVENTHOOK,DWORD event,HWND,LONG,LONG,DWORD,DWORD) {
    // Delivery wakes MsgWaitForMultipleObjects; never query COM in the hook.
    if(event==EVENT_OBJECT_FOCUS)ia2FocusDirty=true;
}
static std::string kanaAlternativesJson(const reading::Result& reading) {
    std::string values="[";
    for(size_t i=0;i<reading.alternatives.size();i++)values+=(i?",":"")+json(reading.alternatives[i]);
    return values+"]";
}
static int runInlineWatcher(DWORD ownerPid=0) {
    inlineOwnerPid=ownerPid;
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    HRESULT initialized=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
    IUIAutomation* automation=nullptr;
    const CLSID automationClass={0xff48dba4,0x60ef,0x4201,{0xaa,0x87,0x54,0x10,0x3e,0xef,0x59,0x4e}};
    HRESULT hr=CoCreateInstance(automationClass,nullptr,CLSCTX_INPROC_SERVER,__uuidof(IUIAutomation),(void**)&automation);
    if(FAILED(hr)||!automation) return 6;
    IUIAutomation2* bounded=nullptr;
    if(SUCCEEDED(automation->QueryInterface(__uuidof(IUIAutomation2),(void**)&bounded)) && bounded) {
        bounded->put_ConnectionTimeout(500);bounded->put_TransactionTimeout(500);bounded->Release();
    }
    HANDLE input=GetStdHandle(STD_INPUT_HANDLE);
    std::string incoming;
    std::wstring previousKey;
    unsigned serial=0;
    std::deque<std::pair<unsigned,std::shared_ptr<InlineSnapshot>>> observations;
    bool running=true,paused=false;
    HWINEVENTHOOK changeHook=SetWinEventHook(EVENT_OBJECT_VALUECHANGE,EVENT_OBJECT_TEXTSELECTIONCHANGED,nullptr,inlineChanged,0,0,WINEVENT_OUTOFCONTEXT|WINEVENT_SKIPOWNPROCESS);
    HWINEVENTHOOK focusHook=SetWinEventHook(EVENT_OBJECT_FOCUS,EVENT_OBJECT_FOCUS,nullptr,inlineChanged,0,0,WINEVENT_OUTOFCONTEXT|WINEVENT_SKIPOWNPROCESS);
    while(running) {
        auto observed=std::make_shared<InlineSnapshot>();
        InlineSnapshot& snapshot=*observed;
        bool valid=!paused && inlineSnapshot(automation,snapshot);
        std::wstring currentKey=valid?snapshot.key:L"invalid:"+std::to_wstring((ULONG_PTR)snapshot.target)+L":"+std::to_wstring(snapshot.reason);
        if(currentKey!=previousKey) {
            // Geometry can settle after a long Korean composition. Preserve
            // only uninterrupted observations of the exact same text/range.
            if(!valid || observations.empty() || !sameInlineLocation(automation,*observations.back().second,snapshot))observations.clear();
            previousKey=currentKey;serial++;
            if(valid) {
                observations.emplace_back(serial,observed);
                if(observations.size()>32)observations.pop_front();
            }
            auto preview=valid && !inlineRoman?reading::convert(snapshot.token):reading::Result{};
            printf("{\"event\":\"input\",\"serial\":%u,\"hwnd\":%llu,\"source\":%s,\"kana\":%s,\"kana_variants\":%s,\"x\":%ld,\"y\":%ld,\"caret_height\":%ld,\"reason\":%d,\"backend\":\"%s\"}\n",serial,(unsigned long long)(ULONG_PTR)snapshot.target,json(valid?snapshot.token:L"").c_str(),json(preview.kana).c_str(),kanaAlternativesJson(preview).c_str(),snapshot.caret.left,snapshot.caret.bottom,snapshot.caret.bottom-snapshot.caret.top,snapshot.reason,snapshot.backend);
            fflush(stdout);
        }
        DWORD available=0;
        if(!PeekNamedPipe(input,nullptr,0,nullptr,&available,nullptr)) break;
        if(available) {
            char buffer[8192];DWORD got=0;
            if(!ReadFile(input,buffer,std::min<DWORD>(available,sizeof buffer),&got,nullptr)) break;
            incoming.append(buffer,got);
            size_t end=0;
            while((end=incoming.find('\n'))!=std::string::npos) {
                std::string command=incoming.substr(0,end);incoming.erase(0,end+1);
                if(command=="QUIT") {running=false;break;}
                if(command=="PAUSE 1" || command=="PAUSE 0") {
                    paused=command=="PAUSE 1";observations.clear();previousKey.clear();continue;
                }
                unsigned requested=0;char hex[4097]={};
                if(sscanf(command.c_str(),"REPLACE %u %4096s",&requested,hex)==2) {
                    auto replacement=fromHex(hex);
                    InlineSnapshot fresh;
                    auto expected=std::find_if(observations.begin(),observations.end(),[&](const auto& entry){return entry.first==requested;});
                    auto captured=expected!=observations.end()?expected->second:nullptr;
                    bool success=!replacement.empty() && valid && captured && refreshInlineSnapshot(automation,*captured,fresh) && sameInlineLocation(automation,*captured,fresh);
                    observations.clear();previousKey.clear();valid=false;
                    if(success) {
                        CommitSpaceScope probe;
                        auto settled=settleInlineComposition(automation,fresh);
                        const InlineSnapshot* selected=settled.get();
                        success=selected && prepareInlineReplacement(automation,*selected) && GetForegroundWindow()==fresh.target;
                        if(success) {
                            GUITHREADINFO focus={sizeof focus};
                            HWND direct=fresh.native&&!fresh.edit.scintilla?fresh.edit.control:nullptr;
                            if(!direct && GetGUIThreadInfo(0,&focus) && nativeEditClass(focus.hwndFocus))direct=focus.hwndFocus;
                            if(selected->ia2) {
                                success=replaceIa2(*selected->ia2,replacement);
                            } else if(direct) {
                                // One marshalled edit operation on the owner's UI
                                // thread preserves UTF-16 order and undo history.
                                DWORD_PTR answer=0;
                                success=editMessage(direct,EM_REPLACESEL,TRUE,(LPARAM)replacement.c_str(),answer);
                            } else {
                            std::vector<INPUT> keys;
                            for(auto c:replacement) {
                                INPUT key={};key.type=INPUT_KEYBOARD;key.ki.wScan=c;key.ki.dwFlags=KEYEVENTF_UNICODE;keys.push_back(key);
                                key.ki.dwFlags|=KEYEVENTF_KEYUP;keys.push_back(key);
                            }
                            success=SendInput((UINT)keys.size(),keys.data(),sizeof(INPUT))==keys.size();
                            }
                        }
                    }
                    printf("{\"event\":\"replace\",\"serial\":%u,\"success\":%s}\n",requested,success?"true":"false");fflush(stdout);
                }
            }
        }
        MSG message;
        while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)) {TranslateMessage(&message);DispatchMessageW(&message);}
        MsgWaitForMultipleObjects(0,nullptr,FALSE,valid?8:16,QS_ALLINPUT);
    }
    if(changeHook)UnhookWinEvent(changeHook);
    if(focusHook)UnhookWinEvent(focusHook);
    observations.clear();clearIa2FocusCache();automation->Release();if(SUCCEEDED(initialized)) CoUninitialize();return 0;
}
