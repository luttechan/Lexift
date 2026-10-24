// UI Automation works across process boundaries without injecting a text service.
#include <uiautomation.h>
#include <algorithm>

struct InlineSnapshot {
    HWND target=nullptr;
    std::wstring token,key;
    RECT caret={};
    IUIAutomationTextRange* range=nullptr;
    int reason=0;
    ~InlineSnapshot() {if(range) range->Release();}
};
static bool hangulCharacter(wchar_t c) {
    return (c>=0xac00 && c<=0xd7a3) || (c>=0x3131 && c<=0x3163) ||
        (c>=0x1100 && c<=0x11ff) || c==L'-' || c==L'ー';
}
static bool inlineSnapshot(IUIAutomation* automation,InlineSnapshot& result) {
    result.target=GetForegroundWindow();
    DWORD pid=0;GetWindowThreadProcessId(result.target,&pid);
    if(!pid || pid==GetCurrentProcessId()) {result.reason=1;return false;}
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
    if(password || !enabled || (type!=UIA_EditControlTypeId && type!=UIA_DocumentControlTypeId)) {element->Release();result.reason=type;return false;}
    IUIAutomationTextPattern* pattern=nullptr;
    HRESULT hr=element->GetCurrentPatternAs(UIA_TextPatternId,__uuidof(IUIAutomationTextPattern),(void**)&pattern);
    element->Release();
    if(FAILED(hr) || !pattern) {result.reason=3;return false;}
    IUIAutomationTextRangeArray* array=nullptr;
    pattern->GetSelection(&array);pattern->Release();
    if(!array) {result.reason=4;return false;}
    int count=0;array->get_Length(&count);
    IUIAutomationTextRange* caret=nullptr;
    if(count==1) array->GetElement(0,&caret);
    array->Release();
    if(!caret) {result.reason=5;return false;}
    BSTR selected=nullptr;caret->GetText(1,&selected);
    bool collapsed=!selected || SysStringLen(selected)==0;SysFreeString(selected);
    if(!collapsed) {caret->Release();result.reason=6;return false;}
    VARIANT readOnly;VariantInit(&readOnly);
    caret->GetAttributeValue(UIA_IsReadOnlyAttributeId,&readOnly);
    bool locked=readOnly.vt==VT_BOOL && readOnly.boolVal==VARIANT_TRUE;
    VariantClear(&readOnly);
    if(locked) {caret->Release();result.reason=7;return false;}
    IUIAutomationTextRange* preceding=nullptr;caret->Clone(&preceding);
    if(!preceding) {caret->Release();result.reason=8;return false;}
    int moved=0;preceding->MoveEndpointByUnit(TextPatternRangeEndpoint_Start,TextUnit_Character,-256,&moved);
    BSTR content=nullptr;preceding->GetText(1024,&content);
    std::wstring prefix=content?std::wstring(content,SysStringLen(content)):L"";
    SysFreeString(content);preceding->Release();
    size_t start=prefix.size();
    while(start && hangulCharacter(prefix[start-1])) start--;
    result.token=prefix.substr(start);
    if(result.token.empty() || result.token.size()>200) {caret->Release();result.reason=9;return false;}
    result.range=caret;
    caret->MoveEndpointByUnit(TextPatternRangeEndpoint_Start,TextUnit_Character,-(int)result.token.size(),&moved);
    BSTR verify=nullptr;caret->GetText(256,&verify);
    std::wstring actual=verify?std::wstring(verify,SysStringLen(verify)):L"";SysFreeString(verify);
    if(actual!=result.token) {result.reason=10;return false;}
    SAFEARRAY* bounds=nullptr;caret->GetBoundingRectangles(&bounds);
    if(bounds) {
        LONG low=0,high=-1;SafeArrayGetLBound(bounds,1,&low);SafeArrayGetUBound(bounds,1,&high);
        if(high-low>=3) {
            double* values=nullptr;
            if(SUCCEEDED(SafeArrayAccessData(bounds,(void**)&values))) {
                int index=((high-low+1)/4-1)*4;
                result.caret={(LONG)(values[index]+values[index+2]),(LONG)values[index+1],(LONG)(values[index]+values[index+2]),(LONG)(values[index+1]+values[index+3])};
                SafeArrayUnaccessData(bounds);
            }
        }
        SafeArrayDestroy(bounds);
    }
    if(!result.caret.bottom) {
        GUITHREADINFO info={sizeof info};
        if(GetGUIThreadInfo(0,&info) && info.hwndCaret) {
            POINT point={info.rcCaret.left,info.rcCaret.bottom};ClientToScreen(info.hwndCaret,&point);
            result.caret={point.x,point.y-20,point.x,point.y};
        }
    }
    // Compare the surrounding text and position again before replacement.
    result.key=std::to_wstring((ULONG_PTR)result.target)+identity+L"|"+prefix+L"|"+
        std::to_wstring(result.caret.left)+L","+std::to_wstring(result.caret.bottom);
    return true;
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
static int runInlineWatcher() {
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
    bool running=true;
    while(running) {
        InlineSnapshot snapshot;
        bool valid=inlineSnapshot(automation,snapshot);
        std::wstring currentKey=valid?snapshot.key:L"invalid:"+std::to_wstring((ULONG_PTR)snapshot.target)+L":"+std::to_wstring(snapshot.reason);
        if(currentKey!=previousKey) {
            previousKey=currentKey;serial++;
            printf("{\"event\":\"input\",\"serial\":%u,\"hwnd\":%llu,\"source\":%s,\"x\":%ld,\"y\":%ld,\"reason\":%d}\n",serial,(unsigned long long)(ULONG_PTR)snapshot.target,json(valid?snapshot.token:L"").c_str(),snapshot.caret.left,snapshot.caret.bottom,snapshot.reason);
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
                unsigned requested=0;char hex[4097]={};
                if(sscanf(command.c_str(),"REPLACE %u %4096s",&requested,hex)==2) {
                    auto replacement=fromHex(hex);
                    InlineSnapshot fresh;
                    bool success=!replacement.empty() && inlineSnapshot(automation,fresh) && requested==serial && valid && fresh.key==snapshot.key;
                    if(success) {
                        success=SUCCEEDED(fresh.range->Select()) && GetForegroundWindow()==fresh.target;
                        if(success) {
                            std::vector<INPUT> keys;
                            for(auto c:replacement) {
                                INPUT key={};key.type=INPUT_KEYBOARD;key.ki.wScan=c;key.ki.dwFlags=KEYEVENTF_UNICODE;keys.push_back(key);
                                key.ki.dwFlags|=KEYEVENTF_KEYUP;keys.push_back(key);
                            }
                            success=SendInput((UINT)keys.size(),keys.data(),sizeof(INPUT))==keys.size();
                        }
                    }
                    printf("{\"event\":\"replace\",\"serial\":%u,\"success\":%s}\n",requested,success?"true":"false");fflush(stdout);
                }
            }
        }
        MSG message;
        while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)) {TranslateMessage(&message);DispatchMessageW(&message);}
        Sleep(valid?35:90);
    }
    automation->Release();if(SUCCEEDED(initialized)) CoUninitialize();return 0;
}
