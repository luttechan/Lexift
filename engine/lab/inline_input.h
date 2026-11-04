// UI Automation works across process boundaries without injecting a text service.
#include <uiautomation.h>
#include <oleacc.h>
#include <algorithm>
#include <cstdint>
#include <deque>
#include <memory>
#include "native_edit_adapter.h"
#include "ia2_adapter.h"
#include "editable_policy.h"
#include "uia_selection.h"
#include "wire_text.h"
static DWORD inlineOwnerPid=0;
static DWORD inlineDesktopPid=0;

struct InlineSnapshot {
    HWND target=nullptr;
    std::wstring token,key,contextKey;
    std::wstring prefix;
    std::wstring protectedText;
    RECT caret={};
    IUIAutomationTextRange* range=nullptr;
    IUIAutomationElement* element=nullptr;
    int reason=0;
    bool blocked=false, native=false, nativeTextValid=false, selected=false;
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
    if(!automation){result.reason=15;return false;}
    result.target=GetForegroundWindow();
    DWORD pid=0;GetWindowThreadProcessId(result.target,&pid);
    if(!pid || pid==GetCurrentProcessId() || pid==inlineOwnerPid || pid==inlineDesktopPid) {result.reason=1;return false;}
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
            if((HWND)native==result.target || (native && GetAncestor((HWND)native,GA_ROOT)==result.target)) {belongs=true;break;}
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
    if(!collapsed) {
        if(!inlineObserveEmpty || FAILED(caret->MoveEndpointByRange(TextPatternRangeEndpoint_End,caret,TextPatternRangeEndpoint_Start))) {
            caret->Release();result.reason=6;return false;
        }
        result.selected=true;
    }
    VARIANT readOnly;VariantInit(&readOnly);
    caret->GetAttributeValue(UIA_IsReadOnlyAttributeId,&readOnly);
    bool writableValue=false;
    if(readOnly.vt!=VT_BOOL && type!=UIA_EditControlTypeId && type!=UIA_DocumentControlTypeId) {
        // Autocomplete/search/address controls can expose ComboBox/Custom,
        // with editability on ValuePattern instead of the text attribute.
        IUIAutomationValuePattern* value=nullptr;BOOL valueReadOnly=TRUE;
        if(SUCCEEDED(element->GetCurrentPatternAs(UIA_ValuePatternId,__uuidof(IUIAutomationValuePattern),(void**)&value)) && value) {
            writableValue=SUCCEEDED(value->get_CurrentIsReadOnly(&valueReadOnly)) && !valueReadOnly;
            value->Release();
        }
    }
    bool explicitReadOnly=readOnly.vt==VT_BOOL && readOnly.boolVal==VARIANT_TRUE;
    bool locked=!editableTextRange(type,readOnly,writableValue);
    VariantClear(&readOnly);
    if(locked) {result.blocked=explicitReadOnly;caret->Release();result.reason=7;return false;}
    IUIAutomationTextRange* preceding=nullptr;caret->Clone(&preceding);
    if(!preceding) {caret->Release();result.reason=8;return false;}
    int moved=0;preceding->MoveEndpointByUnit(TextPatternRangeEndpoint_Start,TextUnit_Character,-256,&moved);
    BSTR content=nullptr;preceding->GetText(1024,&content);
    std::wstring prefix=content?std::wstring(content,SysStringLen(content)):L"";
    SysFreeString(content);
    size_t start=prefix.size();
    if(inlineCommitSpace && start && prefix[start-1]==L' ')--start;
    while(start && hangulCharacter(prefix[start-1])) start--;
    result.token=prefix.substr(start);
    result.prefix=prefix;
    if((result.token.empty() && !inlineObserveEmpty) || result.token.size()>200+(inlineCommitSpace?1:0)) {preceding->Release();caret->Release();result.reason=9;return false;}
    IUIAutomationTextRange* matched=nullptr;
    bool matchedSuffix=result.token.empty()?SUCCEEDED(caret->Clone(&matched)):
        findUiaSuffix(preceding,caret,result.token,&matched);
    preceding->Release();caret->Release();
    if(!matchedSuffix){result.reason=10;return false;}
    result.range=caret=matched;
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
    result.edit=edit;result.selected=edit.selected;result.token=edit.token;result.key=edit.key+L"|"+
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
    result.ia2=snapshot;result.selected=snapshot->selected;result.token=snapshot->token;result.caret=snapshot->caret;
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
    if(!pid || pid==GetCurrentProcessId() || pid==inlineOwnerPid || pid==inlineDesktopPid) {result.reason=1;return false;}
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
static bool prepareInlineReplacement(IUIAutomation* automation,const InlineSnapshot& snapshot,ULONGLONG deadline) {
    if(GetTickCount64()>=deadline)return false;
    if(GetForegroundWindow()!=snapshot.target) return false;
    if(snapshot.ia2) {
        IAccessible* focused=focusedMsaa(snapshot.target);if(!focused)return false;
        bool valid=prepareIa2Replacement(focused,*snapshot.ia2,snapshot.protectedText);
        focused->Release();return valid;
    }
    if(snapshot.native) {
        GUITHREADINFO info={sizeof info};
        if(!GetGUIThreadInfo(0,&info) || info.hwndFocus!=snapshot.edit.control ||
           !selectNativeEdit(snapshot.edit,snapshot.protectedText))return false;
        return GetGUIThreadInfo(0,&info) && info.hwndFocus==snapshot.edit.control;
    }
    if(!automation || !snapshot.range || !snapshot.element || FAILED(snapshot.range->Select()))return false;
    IUIAutomationTextPattern* pattern=nullptr;
    snapshot.element->GetCurrentPatternAs(UIA_TextPatternId,__uuidof(IUIAutomationTextPattern),(void**)&pattern);
    if(!pattern) {
        IUIAutomationTextPattern2* alternate=nullptr;
        if(SUCCEEDED(snapshot.element->GetCurrentPatternAs(UIA_TextPattern2Id,__uuidof(IUIAutomationTextPattern2),(void**)&alternate)) && alternate) {
            alternate->QueryInterface(__uuidof(IUIAutomationTextPattern),(void**)&pattern);alternate->Release();
        }
    }
    if(!pattern)return false;
    bool ready=false;
    do {
        IUIAutomationElement* focused=nullptr;BOOL same=FALSE;
        if(GetForegroundWindow()!=snapshot.target)break;
        if(SUCCEEDED(automation->GetFocusedElement(&focused)) && focused) {
            automation->CompareElements(snapshot.element,focused,&same);focused->Release();
        }
        if(!same)break;
        IUIAutomationTextRangeArray* array=nullptr;pattern->GetSelection(&array);
        ready=selectedUiaRangeMatches(snapshot.range,array,snapshot.token);
        if(array)array->Release();
        if(ready || GetTickCount64()>=deadline)break;
        Sleep(5);
    } while(true);
    pattern->Release();return ready;
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

// Narrow the exact replacement range as well as the displayed reading.
static bool restrictInlineSuffix(InlineSnapshot& snapshot,const std::wstring& protectedText) {
    if(snapshot.selected)return false;
    if(snapshot.token.size()<=protectedText.size() || snapshot.token.compare(0,protectedText.size(),protectedText)!=0)
        return false;
    if(protectedText.empty())return true;
    auto suffix=snapshot.token.substr(protectedText.size());
    if(snapshot.native) {
        if(!restrictNativeEdit(snapshot.edit,protectedText))return false;
    } else if(snapshot.ia2) {
        if(!restrictIa2(*snapshot.ia2,protectedText))return false;
    } else {
        IUIAutomationTextRange* end=nullptr;
        if(FAILED(snapshot.range->Clone(&end)) || !end)return false;
        IUIAutomationTextRange* matched=nullptr;
        bool found=SUCCEEDED(end->MoveEndpointByRange(TextPatternRangeEndpoint_Start,end,TextPatternRangeEndpoint_End)) &&
            findUiaSuffix(snapshot.range,end,suffix,&matched);
        end->Release();
        if(!found)return false;
        snapshot.range->Release();
        snapshot.range=matched;
    }
    snapshot.protectedText=protectedText;
    snapshot.token=std::move(suffix);
    return true;
}

static bool sameTypingAnchor(IUIAutomation* automation,const InlineSnapshot& base,const InlineSnapshot& next) {
    if(base.target!=next.target || base.native!=next.native)return false;
    if(base.native) {
        if(base.edit.control!=next.edit.control || base.edit.scintilla!=next.edit.scintilla ||
           base.edit.start!=next.edit.start)return false;
        if(base.edit.scintilla)
            return base.edit.documentLength-base.edit.end==next.edit.documentLength-next.edit.end;
        return base.edit.fullText.compare(0,base.edit.end,next.edit.fullText,0,base.edit.end)==0 &&
            base.edit.fullText.substr(base.edit.end)==next.edit.fullText.substr(next.edit.end);
    }
    if(base.ia2 || next.ia2) {
        return base.ia2 && next.ia2 && base.ia2->identity && base.ia2->identity==next.ia2->identity &&
            base.ia2->start==next.ia2->start && base.ia2->after==next.ia2->after;
    }
    BOOL same=FALSE;
    if(!automation || !base.element || !next.element ||
       FAILED(automation->CompareElements(base.element,next.element,&same)) || !same ||
       next.token.size()<base.token.size())return false;
    // UIA only reads a bounded prefix. Compare its surviving suffix when the
    // newly typed characters have pushed older context out of that window.
    const size_t added=next.token.size()-base.token.size();
    if(next.prefix.size()<added)return false;
    const size_t before=next.prefix.size()-added;
    const size_t overlap=std::min(base.prefix.size(),before);
    return (overlap || base.prefix.empty()) &&
        base.prefix.compare(base.prefix.size()-overlap,overlap,next.prefix,before-overlap,overlap)==0;
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
static std::shared_ptr<InlineSnapshot> settleInlineComposition(IUIAutomation* automation,const InlineSnapshot& before,ULONGLONG deadline) {
    // A foreign process does not own this app's HIMC/TSF composition. Let its
    // real Korean IME commit naturally, then remove exactly this added space
    // together with the verified original reading. No caret movement keys.
    if(GetForegroundWindow()!=before.target || GetTickCount64()>=deadline)return {};
    INPUT keys[2]={};keys[0].type=keys[1].type=INPUT_KEYBOARD;
    keys[0].ki.wVk=keys[1].ki.wVk=VK_SPACE;keys[1].ki.dwFlags=KEYEVENTF_KEYUP;
    if(SendInput(2,keys,sizeof(INPUT))!=2)return {};
    while(GetTickCount64()<deadline) {
        if(GetForegroundWindow()!=before.target)return {};
        auto after=std::make_shared<InlineSnapshot>();
        if(refreshInlineSnapshot(automation,before,*after) && restrictInlineSuffix(*after,before.protectedText) &&
           sameAfterCommitSpace(automation,before,*after))return after;
        Sleep(5);
    }
    return {};
}
// One atomic keeps the context generation and its key count consistent
// across the hook thread and the accessibility reader.
static std::atomic<uint64_t> typingState{0};
static std::atomic<ULONGLONG> lastTypingStroke{0};
static unsigned typingBoundary() {return (unsigned)(typingState.load()>>32);}
static void resetTyping() {
    auto previous=typingState.load();
    while(!typingState.compare_exchange_weak(previous,((previous>>32)+1)<<32)) {}
}
static bool typingModifierDown() {
    return ((GetAsyncKeyState(VK_CONTROL)|GetAsyncKeyState(VK_MENU)|
             GetAsyncKeyState(VK_LWIN)|GetAsyncKeyState(VK_RWIN)) & 0x8000)!=0;
}
static LRESULT CALLBACK observeTypingKey(int code,WPARAM message,LPARAM data) {
    const LRESULT result=CallNextHookEx(nullptr,code,message,data);
    // The navigation hook consumes candidate selection keys. They must not
    // invalidate the reading just before its replacement request arrives.
    if(!result && code==HC_ACTION && (message==WM_KEYDOWN || message==WM_SYSKEYDOWN)) {
        const auto& key=*reinterpret_cast<const KBDLLHOOKSTRUCT*>(data);
        if(!(inlineCommitSpace && (key.flags&LLKHF_INJECTED))) {
            const DWORD vk=key.vkCode;
            if(typingModifierDown() || (key.flags&LLKHF_INJECTED))resetTyping();
            else if((vk>='A' && vk<='Z') || vk==VK_OEM_MINUS || vk==VK_SUBTRACT) {
                lastTypingStroke=GetTickCount64();
                typingState.fetch_add(1);
            } else if(vk!=VK_SHIFT && vk!=VK_LSHIFT && vk!=VK_RSHIFT && vk!=VK_BACK)resetTyping();
            else if(vk==VK_BACK && (unsigned)typingState.load())lastTypingStroke=GetTickCount64();
        }
    }
    return result;
}
static LRESULT CALLBACK observeTypingMouse(int code,WPARAM message,LPARAM data) {
    if(code==HC_ACTION && (message==WM_LBUTTONDOWN || message==WM_RBUTTONDOWN ||
                          message==WM_MBUTTONDOWN || message==WM_XBUTTONDOWN)) {
        const auto& mouse=*reinterpret_cast<const MSLLHOOKSTRUCT*>(data);
        const HWND hit=WindowFromPoint(mouse.pt);
        const HWND root=hit?GetAncestor(hit,GA_ROOT):nullptr;
        DWORD pid=0;
        GetWindowThreadProcessId(root?root:hit,&pid);
        if(!pid || (pid!=inlineOwnerPid && pid!=inlineDesktopPid))resetTyping();
    }
    return CallNextHookEx(nullptr,code,message,data);
}
class TypingObserver {
    HANDLE ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    HANDLE stop=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    HANDLE thread=nullptr;
    std::atomic<bool> installed{false};

    static DWORD WINAPI loop(void* argument) {
        auto& observer=*static_cast<TypingObserver*>(argument);
        MSG message;
        PeekMessageW(&message,nullptr,0,0,PM_NOREMOVE);
        HINSTANCE module=GetModuleHandleW(nullptr);
        HHOOK keys=SetWindowsHookExW(WH_KEYBOARD_LL,observeTypingKey,module,0);
        HHOOK mouse=SetWindowsHookExW(WH_MOUSE_LL,observeTypingMouse,module,0);
        observer.installed=keys && mouse;
        SetEvent(observer.ready);
        while(keys && mouse && MsgWaitForMultipleObjects(1,&observer.stop,FALSE,INFINITE,QS_ALLINPUT)==WAIT_OBJECT_0+1) {
            while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)) {
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
        }
        if(keys)UnhookWindowsHookEx(keys);
        if(mouse)UnhookWindowsHookEx(mouse);
        return 0;
    }

public:
    bool start() {
        if(!ready || !stop)return false;
        thread=CreateThread(nullptr,0,loop,this,0,nullptr);
        return thread && WaitForSingleObject(ready,2000)==WAIT_OBJECT_0 && installed;
    }
    ~TypingObserver() {
        if(thread) {
            SetEvent(stop);
            WaitForSingleObject(thread,INFINITE);
            CloseHandle(thread);
        }
        if(ready)CloseHandle(ready);
        if(stop)CloseHandle(stop);
    }
};
static void CALLBACK inlineChanged(HWINEVENTHOOK,DWORD event,HWND,LONG,LONG,DWORD,DWORD) {
    // Delivery wakes MsgWaitForMultipleObjects; never query COM in the hook.
    if(event==EVENT_OBJECT_FOCUS) { ia2FocusDirty=true; resetTyping(); }
}
static std::string kanaAlternativesJson(const reading::Result& reading) {
    std::string values="[";
    for(size_t i=0;i<reading.alternatives.size();i++)values+=(i?",":"")+json(reading.alternatives[i]);
    return values+"]";
}
static int runInlineWatcher(DWORD ownerPid=0) {
    inlineOwnerPid=ownerPid;
    wchar_t desktopPid[16]={};
    const DWORD pidLength=GetEnvironmentVariableW(L"LEXIFT_DESKTOP_PID",desktopPid,16);
    if(pidLength && pidLength<16)inlineDesktopPid=(DWORD)wcstoul(desktopPid,nullptr,10);
    inlineObserveEmpty=!inlineRoman;
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    HRESULT initialized=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
    TypingObserver observer;
    if(!inlineRoman && !observer.start()) {
        if(SUCCEEDED(initialized))CoUninitialize();
        return 5;
    }
    IUIAutomation* automation=nullptr;
    const CLSID automationClass={0xff48dba4,0x60ef,0x4201,{0xaa,0x87,0x54,0x10,0x3e,0xef,0x59,0x4e}};
    const CLSID boundedClass={0xe22ad333,0xb25f,0x460c,{0x83,0xd0,0x05,0x81,0x10,0x73,0x95,0xc9}};
    HRESULT hr=CoCreateInstance(boundedClass,nullptr,CLSCTX_INPROC_SERVER,__uuidof(IUIAutomation),(void**)&automation);
    if(FAILED(hr)||!automation)hr=CoCreateInstance(automationClass,nullptr,CLSCTX_INPROC_SERVER,__uuidof(IUIAutomation),(void**)&automation);
    IUIAutomation2* bounded=nullptr;
    if(automation && SUCCEEDED(automation->QueryInterface(__uuidof(IUIAutomation2),(void**)&bounded)) && bounded) {
        bounded->put_ConnectionTimeout(500);bounded->put_TransactionTimeout(500);bounded->Release();
    }
    HANDLE input=GetStdHandle(STD_INPUT_HANDLE);
    std::string incoming;
    std::wstring previousKey;
    unsigned serial=0;
    std::deque<std::pair<unsigned,std::shared_ptr<InlineSnapshot>>> observations;
    bool running=true,paused=false;ULONGLONG heartbeat=0;
    std::shared_ptr<InlineSnapshot> baseline;
    unsigned boundary=typingBoundary(), baselineStrokes=0;
    std::wstring lastRawToken;
    HWINEVENTHOOK changeHook=SetWinEventHook(EVENT_OBJECT_VALUECHANGE,EVENT_OBJECT_TEXTSELECTIONCHANGED,nullptr,inlineChanged,0,0,WINEVENT_OUTOFCONTEXT|WINEVENT_SKIPOWNPROCESS);
    HWINEVENTHOOK focusHook=SetWinEventHook(EVENT_OBJECT_FOCUS,EVENT_OBJECT_FOCUS,nullptr,inlineChanged,0,0,WINEVENT_OUTOFCONTEXT|WINEVENT_SKIPOWNPROCESS);
    while(running) {
        MSG message;
        while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)) {TranslateMessage(&message);DispatchMessageW(&message);}
        ULONGLONG now=GetTickCount64();
        if(now-heartbeat>=1000){printf("{\"event\":\"heartbeat\",\"uia\":%s}\n",automation?"true":"false");fflush(stdout);heartbeat=now;}
        auto observed=std::make_shared<InlineSnapshot>();
        InlineSnapshot& snapshot=*observed;
        bool valid=!paused && inlineSnapshot(automation,snapshot);
        if(!inlineRoman) {
            const auto inputState=typingState.load();
            const auto currentBoundary=(unsigned)(inputState>>32);
            const auto strokes=(unsigned)inputState;
            if(boundary!=currentBoundary) {
                boundary=currentBoundary;baseline.reset();observations.clear();
            }
            const auto raw=snapshot.token;
            const bool recent=raw==lastRawToken || GetTickCount64()-lastTypingStroke<=500;
            const bool anchored=valid && baseline && !typingModifierDown() &&
                strokes>baselineStrokes && recent && raw.size()>=baseline->token.size() &&
                raw.size()-baseline->token.size()<=strokes-baselineStrokes &&
                raw.compare(0,baseline->token.size(),baseline->token)==0 &&
                sameTypingAnchor(automation,*baseline,snapshot) && boundary==typingBoundary();
            if(anchored && (snapshot.selected || raw==baseline->token)) {
                // A hardware key reaches the hook before its IME text is
                // visible. Keep the pre-key baseline until the text arrives.
                valid=false;
                lastRawToken=raw;
            } else if(anchored && restrictInlineSuffix(snapshot,baseline->token)) {
                lastRawToken=raw;
            } else {
                baseline=valid?observed:nullptr;
                baselineStrokes=strokes;
                lastRawToken=raw;
                valid=false;
            }
        }
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
            if(incoming.size()>131072)break;
            size_t end=0;
            while((end=incoming.find('\n'))!=std::string::npos) {
                std::string command=incoming.substr(0,end);incoming.erase(0,end+1);
                if(command=="QUIT") {running=false;break;}
                if(command=="PAUSE 1" || command=="PAUSE 0") {
                    paused=command=="PAUSE 1";resetTyping();observations.clear();previousKey.clear();continue;
                }
                if(command.compare(0,8,"REPLACE ")==0) {
                    unsigned requested=0;std::wstring replacement;
                    if(!parseReplacementCommand(command,requested,replacement)) {
                        printf("{\"event\":\"replace\",\"serial\":%u,\"success\":false}\n",requested);fflush(stdout);continue;
                    }
                    ULONGLONG deadline=GetTickCount64()+1800;
                    InlineSnapshot fresh;
                    auto expected=std::find_if(observations.begin(),observations.end(),[&](const auto& entry){return entry.first==requested;});
                    auto captured=expected!=observations.end()?expected->second:nullptr;
                    const auto commitInputState=typingState.load();
                    bool success=!replacement.empty() && valid && captured &&
                        (inlineRoman || (boundary==(unsigned)(commitInputState>>32) && !typingModifierDown())) &&
                        refreshInlineSnapshot(automation,*captured,fresh) &&
                        restrictInlineSuffix(fresh,captured->protectedText) && sameInlineLocation(automation,*captured,fresh) &&
                        (inlineRoman || commitInputState==typingState.load());
                    observations.clear();previousKey.clear();valid=false;
                    if(success) {
                        CommitSpaceScope probe;
                        auto settled=settleInlineComposition(automation,fresh,deadline);
                        const InlineSnapshot* selected=settled.get();
                        success=selected && (inlineRoman || commitInputState==typingState.load()) &&
                            prepareInlineReplacement(automation,*selected,deadline) &&
                            (inlineRoman || commitInputState==typingState.load()) &&
                            GetForegroundWindow()==fresh.target && GetTickCount64()<deadline;
                        if(success) {
                            HWND direct=fresh.native&&!fresh.edit.scintilla?fresh.edit.control:nullptr;
                            if(selected->ia2) {
                                success=replaceIa2(*selected->ia2,replacement,deadline);
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
                    resetTyping();
                    printf("{\"event\":\"replace\",\"serial\":%u,\"success\":%s}\n",requested,success?"true":"false");fflush(stdout);
                }
            }
        }
        MsgWaitForMultipleObjects(0,nullptr,FALSE,valid?8:16,QS_ALLINPUT);
    }
    if(changeHook)UnhookWinEvent(changeHook);
    if(focusHook)UnhookWinEvent(focusHook);
    observations.clear();clearIa2FocusCache();if(automation)automation->Release();if(SUCCEEDED(initialized)) CoUninitialize();return 0;
}
