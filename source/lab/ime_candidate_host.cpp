// Lexift & ANV 0.8 experiment. Own RichEdit text host, no global hooks.
// COM declarations follow Microsoft's msctf.h; MinGW omits candidate interfaces.
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <msctf.h>
#include <richedit.h>
#include <commctrl.h>
#include <shellapi.h>
#include <imm.h>
#include <stdio.h>
#include <string>
#include <vector>
#include "hangul_reading.h"

struct CandidateUI : ITfUIElement {
    virtual HRESULT STDMETHODCALLTYPE GetUpdatedFlags(DWORD*) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetDocumentMgr(ITfDocumentMgr**) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetCount(UINT*) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetSelection(UINT*) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetString(UINT,BSTR*) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetPageIndex(UINT*,UINT,UINT*) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetPageIndex(UINT*,UINT) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetCurrentPage(UINT*) = 0;
};
struct CandidateBehavior : CandidateUI {
    virtual HRESULT STDMETHODCALLTYPE SetSelection(UINT) = 0;
    virtual HRESULT STDMETHODCALLTYPE Finalize() = 0;
    virtual HRESULT STDMETHODCALLTYPE Abort() = 0;
};
static const IID candidateIID = {0xea1ea138,0x19df,0x11d7,{0xa6,0xd2,0,6,0x5b,0x84,0x43,0x5c}};
static const IID behaviorIID = {0x85fad185,0x58ce,0x497a,{0x94,0x60,0x35,0x53,0x66,0xb6,0x4b,0x9a}};
static const CLSID threadCLSID = {0x529a9e6b,0x6587,0x4f23,{0xab,0x9e,0x9c,0x7d,0x68,0x3e,0x3c,0x50}};
static const CLSID profilesCLSID = {0x33c53a50,0xf456,0x4884,{0xb0,0x49,0x85,0xfd,0x64,0x3e,0xcf,0xed}};
static HWND windowHandle, editor, outputLabel;
static HWND sourceEditor,readingEditor,noteLabel,convertButton;
static WNDPROC previousEditProc;
static WNDPROC previousJapaneseProc;
static std::wstring hangulInput;
static bool hangulTest=false;
static bool buttonTest=false;
static std::wstring feeding;
static int feedStep=0;
static bool feedingActive=false;
static ITfThreadMgrEx* tm;
static TfClientId queryClientId=0;
static ITfUIElementMgr* ui;
static ITfSource* source;
static DWORD cookie = TF_INVALID_COOKIE;
static FILE* logFile;
static bool nativeUI = false, automatic = false, gotCandidates = false, inputAborted = false;
static bool useBehavior=false, cancelTest=false, abortCandidate=false;
static bool queryLive=false;
static bool queryServer=false,queryActive=false,queryInitialized=false;
static bool sharedQueryDesktop=false,ignoreLayoutCache=false,tickRunning=false;
static unsigned queryRetries=0;
static unsigned queryId=0;
static std::string queryInput;
static std::vector<std::wstring> queryStrings;
static std::vector<std::wstring> queryReadings,mergedCandidates,mergedReadings;
static size_t queryReadingIndex=0;
static bool queryCollect=false;
static DWORD lastQueryUpdate=0;
static bool queryDocument=false,queryComposition=false,queryConverted=false;
static bool actionsOK=true;
static std::wstring expectedCommit;
static std::wstring screenshotPath;
static int step = 0;
static std::wstring romaji = L"watashi";
static UINT lang = 0x0411;
static UINT candidateCount = 0;
static DWORD activeElement = DWORD(-1);
static void activateInputLanguage(UINT language);
static bool prepareConversion(bool feed);
static void updateReading();
static void feedTick();

static HRESULT controlCandidate(bool finalize, bool abort) {
    if(GetForegroundWindow()!=windowHandle || GetFocus()!=editor) {inputAborted=true;return E_ABORT;}
    ITfUIElement* element=nullptr;
    CandidateBehavior* behavior=nullptr;
    HRESULT result=ui->GetUIElement(activeElement,&element);
    if(SUCCEEDED(result) && element) {
        result=element->QueryInterface(behaviorIID,(void**)&behavior);
        if(SUCCEEDED(result) && behavior) {
            if(!abort && !finalize) {
                BSTR first=nullptr;
                if(SUCCEEDED(behavior->GetString(0,&first)) && first) expectedCommit.assign(first,SysStringLen(first));
                SysFreeString(first);
            }
            result=abort?behavior->Abort():finalize?behavior->Finalize():behavior->SetSelection(0);
            behavior->Release();
        }
        element->Release();
    }
    return result;
}
static void screenshot() {
    if(screenshotPath.empty()) return;
    RECT rect;GetClientRect(windowHandle,&rect);
    int width=rect.right,height=rect.bottom;
    HDC dc=GetDC(windowHandle),memory=CreateCompatibleDC(dc);
    BITMAPINFO info={};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
    info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=-height;
    info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
    void* pixels=nullptr;
    HBITMAP bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&pixels,nullptr,0);
    if(bitmap) {
        HGDIOBJ old=SelectObject(memory,bitmap);
        if(BitBlt(memory,0,0,width,height,dc,0,0,SRCCOPY)) {
            FILE* file=_wfopen(screenshotPath.c_str(),L"wb");
            if(file) {
                BITMAPFILEHEADER header={};header.bfType=0x4d42;header.bfOffBits=sizeof header+sizeof info.bmiHeader;
                header.bfSize=header.bfOffBits+width*height*4;
                fwrite(&header,sizeof header,1,file);fwrite(&info.bmiHeader,sizeof info.bmiHeader,1,file);
                fwrite(pixels,width*height*4,1,file);fclose(file);
            }
        }
        SelectObject(memory,old);DeleteObject(bitmap);
    }
    DeleteDC(memory);ReleaseDC(windowHandle,dc);
}

static std::string utf8(const std::wstring& s) {
    int n=WideCharToMultiByte(CP_UTF8,0,s.data(),(int)s.size(),nullptr,0,nullptr,nullptr);
    std::string out(n,0);
    if(n) WideCharToMultiByte(CP_UTF8,0,s.data(),(int)s.size(),out.data(),n,nullptr,nullptr);
    return out;
}
static std::string json(const std::wstring& s) {
    std::string out="\"";
    for(unsigned char c:utf8(s)) {
        if(c=='"' || c=='\\') {out+='\\';out+=c;}
        else if(c<32) {char b[8];snprintf(b,sizeof b,"\\u%04x",c);out+=b;}
        else out+=c;
    }
    return out+'"';
}
static void event(const char* name, HRESULT status=S_OK) {
    if(logFile) {fprintf(logFile,"{\"event\":\"%s\",\"hr\":\"0x%08lX\",\"tick\":%lu}\n",name,(unsigned long)status,GetTickCount());fflush(logFile);}
    else if(queryServer) {fprintf(stderr,"%s 0x%08lX\n",name,(unsigned long)status);fflush(stderr);}
}
#include "inline_input.h"
static void snapshot(DWORD id, const char* reason) {
    if(queryServer && (!queryActive || !queryCollect))return;
    if(!queryLive && GetFocus()!=editor) return;
    ITfUIElement* element=nullptr;
    if(FAILED(ui->GetUIElement(id,&element)) || !element) return;
    CandidateUI* list=nullptr;
    HRESULT queried=element->QueryInterface(candidateIID,(void**)&list);
    element->Release();
    if(FAILED(queried) || !list) return;
    UINT count=0,selection=0,page=0,pageCount=0;
    DWORD flags=0;
    list->GetUpdatedFlags(&flags);
    HRESULT countHR=list->GetCount(&count);
    HRESULT selectionHR=list->GetSelection(&selection);
    list->GetCurrentPage(&page);
    list->GetPageIndex(nullptr,0,&pageCount);
    std::vector<UINT> pages(pageCount<1000?pageCount:0);
    if(!pages.empty()) list->GetPageIndex(pages.data(),(UINT)pages.size(),&pageCount);
    std::wstring display=L"변환 후보 ("+std::to_wstring(count)+L"개)\r\n";
    UINT displayStart=selectionHR==S_OK?(selection/8)*8:0;
    if(queryLive) {queryStrings.clear();lastQueryUpdate=GetTickCount();}
    std::string strings="[";
    UINT extracted=0;
    for(UINT i=0;SUCCEEDED(countHR) && i<count && i<200;i++) {
        BSTR str=nullptr;
        if(SUCCEEDED(list->GetString(i,&str)) && str) {
            std::wstring text(str,SysStringLen(str));
            if(queryLive) queryStrings.push_back(text);
            if(extracted++) strings+=',';
            strings+=json(text);
            if(i>=displayStart && i<displayStart+8) display+=(selectionHR==S_OK && i==selection?L"> ":L"  ")+std::to_wstring(i+1)+L". "+text+L"\r\n";
        }
        SysFreeString(str);
    }
    strings+=']';
    if(count>8) display+=L"… 화살표로 계속 선택\r\n";
    CandidateBehavior* behavior=nullptr;
    bool canControl=SUCCEEDED(list->QueryInterface(behaviorIID,(void**)&behavior));
    if(behavior) behavior->Release();
    if(extracted) {gotCandidates=true;candidateCount=extracted;activeElement=id;}
    SetWindowTextW(outputLabel,display.c_str());
    if(logFile) {
        fprintf(logFile,"{\"event\":\"candidates\",\"reason\":\"%s\",\"id\":%lu,\"count\":%u,\"extracted\":%u,\"selection\":%s,\"page\":%u,\"behavior\":%s,\"strings\":%s}\n",
            reason,id,count,extracted,selectionHR==S_OK?std::to_string(selection).c_str():"null",page,canControl?"true":"false",strings.c_str());
        fflush(logFile);
    }
    list->Release();
}
class Sink : public ITfUIElementSink {
    LONG refs=1;
public:
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid,void** out) override {
        if(!out) return E_POINTER;
        *out=nullptr;
        if(IsEqualIID(iid,IID_IUnknown)||IsEqualIID(iid,__uuidof(ITfUIElementSink))) {*out=this;AddRef();return S_OK;}
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override {return InterlockedIncrement(&refs);}
    ULONG STDMETHODCALLTYPE Release() override {LONG n=InterlockedDecrement(&refs);if(!n) delete this;return n;}
    HRESULT STDMETHODCALLTYPE BeginUIElement(DWORD id,BOOL* show) override {
        *show=TRUE;
        ITfUIElement* e=nullptr; CandidateUI* c=nullptr;
        if(SUCCEEDED(ui->GetUIElement(id,&e)) && e) {
            if(SUCCEEDED(e->QueryInterface(candidateIID,(void**)&c)) && c) {
                if(queryLive || GetFocus()==editor) {*show=nativeUI;activeElement=id;}
                c->Release();
            }
            e->Release();
        }
        event("begin");
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE UpdateUIElement(DWORD id) override {snapshot(id,"update");return S_OK;}
    HRESULT STDMETHODCALLTYPE EndUIElement(DWORD id) override {
        if(id==activeElement) {activeElement=DWORD(-1);SetWindowTextW(outputLabel,L"변환을 확정하거나 취소했습니다.");}
        event("end");return S_OK;
    }
};

// Used only by this explicit self-test. Abort on focus change before every key.
static bool key(WORD vk) {
    if(GetForegroundWindow()!=windowHandle || GetFocus()!=editor) {
        if(logFile) fprintf(logFile,"{\"event\":\"focus_details\",\"foreground_is_host\":%s,\"focus_is_editor\":%s}\n",GetForegroundWindow()==windowHandle?"true":"false",GetFocus()==editor?"true":"false");
        inputAborted=true;event("focus_abort",E_ABORT);return false;
    }
    INPUT events[2]={};
    for(auto& x:events) {x.type=INPUT_KEYBOARD;x.ki.wVk=vk;}
    events[1].ki.dwFlags=KEYEVENTF_KEYUP;
    if(SendInput(2,events,sizeof(INPUT))!=2) {inputAborted=true;event("sendinput_failed",E_FAIL);return false;}
    return true;
}
static std::wstring textOf(HWND field) {
    int length=GetWindowTextLengthW(field);
    std::wstring text(length+1,L'\0');
    GetWindowTextW(field,text.data(),length+1);text.resize(length);return text;
}
static bool activateProfile(ITfInputProcessorProfiles* profiles,LANGID language) {
    if(!profiles)return false;
    HRESULT changed=profiles->ChangeCurrentLanguage(language);event("change_query_language",changed);
    GUID category={0x34745c63,0xb2f0,0x4784,{0x8b,0x67,0x5e,0x12,0xc8,0x70,0x1a,0x31}},clsid={},profile={};
    ITfInputProcessorProfileMgr* manager=nullptr;
    profiles->QueryInterface(__uuidof(ITfInputProcessorProfileMgr),(void**)&manager);
    auto activate=[&](REFCLSID clsid,REFGUID profile){
        // Flags zero affects this helper thread only. Never enable a profile
        // in the registry or switch the user's foreground application's IME.
        HRESULT result=manager?manager->ActivateProfile(TF_PROFILETYPE_INPUTPROCESSOR,language,clsid,profile,nullptr,0):E_NOINTERFACE;
        if(result!=S_OK)result=profiles->ActivateLanguageProfile(clsid,language,profile);
        event("activate_query_profile",result);return result==S_OK;
    };
    bool activated=false;
    if(SUCCEEDED(profiles->GetDefaultLanguageProfile(language,category,&clsid,&profile)))activated=activate(clsid,profile);
    if(!activated){
        IEnumTfLanguageProfiles* items=nullptr;
        if(SUCCEEDED(profiles->EnumLanguageProfiles(language,&items)) && items){
            TF_LANGUAGEPROFILE value={};ULONG fetched=0;
            while(items->Next(1,&value,&fetched)==S_OK){
                BOOL enabled=FALSE;
                if(!IsEqualGUID(value.catid,category) ||
                   FAILED(profiles->IsEnabledLanguageProfile(value.clsid,language,value.guidProfile,&enabled)) || !enabled)continue;
                if(activate(value.clsid,value.guidProfile)){activated=true;break;}
            }
            items->Release();
        }
    }
    if(manager)manager->Release();
    return activated;
}
static void activateInputLanguage(UINT language) {
    ITfInputProcessorProfiles* p=nullptr;
    if(SUCCEEDED(CoCreateInstance(profilesCLSID,nullptr,CLSCTX_INPROC_SERVER,__uuidof(ITfInputProcessorProfiles),(void**)&p))) {
        activateProfile(p,(LANGID)language);
        p->Release();
    }
    HWND field=queryLive?editor:GetFocus();
    HIMC context=ImmGetContext(field);
    if(context) {
        ImmSetOpenStatus(context,TRUE);
        ImmSetConversionStatus(context,language==0x0412?IME_CMODE_NATIVE:IME_CMODE_NATIVE|IME_CMODE_FULLSHAPE|IME_CMODE_ROMAN,0);
        ImmReleaseContext(field,context);
    }
}
static void updateReading() {
    auto result=reading::convert(textOf(sourceEditor));
    SetWindowTextW(readingEditor,result.kana.c_str());
    SetWindowTextW(noteLabel,result.ok()?result.note.c_str():result.error.c_str());
    EnableWindow(convertButton,result.ok());
}
static bool prepareConversion(bool feed) {
    auto result=reading::convert(textOf(readingEditor));
    if(!result.ok()) {SetWindowTextW(noteLabel,result.error.c_str());return false;}
    KillTimer(windowHandle,2);feedingActive=false;
    SetFocus(editor);activateInputLanguage(lang);
    HIMC context=ImmGetContext(editor);
    if(context) {ImmNotifyIME(context,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,context);}
    SetWindowTextW(editor,L"");
    romaji=result.romaji;inputAborted=false;
    if(logFile) {fprintf(logFile,"{\"event\":\"reading\",\"source\":%s,\"kana\":%s,\"romaji\":%s}\n",json(textOf(sourceEditor)).c_str(),json(result.kana).c_str(),json(result.romaji).c_str());fflush(logFile);}
    if(feed) {feeding=result.romaji;feedStep=0;feedingActive=true;SetTimer(windowHandle,2,40,nullptr);}
    return true;
}
static bool readingKey(wchar_t c) {
    if(c>=L'a' && c<=L'z') return key(WORD(c-L'a'+L'A'));
    if(c==L'\'') return key(VK_OEM_7);
    if(c==L'-') return key(VK_OEM_MINUS);
    if(c==L'.') return key(VK_OEM_PERIOD);
    if(c==L',') return key(VK_OEM_COMMA);
    return false;
}
static void feedTick() {
    if(GetForegroundWindow()!=windowHandle || GetFocus()!=editor) {
        KillTimer(windowHandle,2);feedingActive=false;SetWindowTextW(noteLabel,L"입력창을 벗어나 변환을 중단했습니다. 변환 버튼으로 다시 실행할 수 있습니다.");return;
    }
    feedStep++;
    int end=8+(int)feeding.size();
    if(feedStep>=8 && feedStep<end && !readingKey(feeding[feedStep-8])) {KillTimer(windowHandle,2);feedingActive=false;return;}
    if(feedStep==end+4 || feedStep==end+9) key(VK_SPACE);
    if(feedStep==end+10) {KillTimer(windowHandle,2);feedingActive=false;}
}
static LRESULT CALLBACK japaneseProc(HWND field,UINT msg,WPARAM w,LPARAM l) {
    if(msg==WM_KEYDOWN && w==VK_ESCAPE && feedingActive) {
        KillTimer(windowHandle,2);feedingActive=false;
        SetWindowTextW(noteLabel,L"변환을 중단했습니다. 발음이나 독음을 수정한 뒤 다시 변환할 수 있습니다.");
    }
    return CallWindowProcW(previousJapaneseProc,field,msg,w,l);
}
static LRESULT CALLBACK readingProc(HWND field,UINT msg,WPARAM w,LPARAM l) {
    if(msg==WM_KEYDOWN && w==VK_RETURN) {
        HIMC c=ImmGetContext(field);
        LONG composing=c?ImmGetCompositionStringW(c,GCS_COMPSTR,nullptr,0):0;
        if(c) ImmReleaseContext(field,c);
        if(composing<=0) {PostMessageW(windowHandle,WM_COMMAND,5003,0);return 0;}
    }
    return CallWindowProcW(previousEditProc,field,msg,w,l);
}
static void finish() {
    wchar_t text[4096]={};GetWindowTextW(editor,text,4096);
    bool passed=gotCandidates && !inputAborted && actionsOK &&
        (cancelTest?text[0]==0:useBehavior&&!expectedCommit.empty()?std::wstring(text)==expectedCommit:text[0]!=0);
    if(logFile) {
        fprintf(logFile,"{\"event\":\"summary\",\"passed\":%s,\"got_candidates\":%s,\"extracted\":%u,\"input_aborted\":%s,\"editor_text\":%s}\n",
            passed?"true":"false",gotCandidates?"true":"false",candidateCount,inputAborted?"true":"false",json(text).c_str());fflush(logFile);
    }
    if(!passed) actionsOK=false;
    DestroyWindow(windowHandle);
}
class CompositionReader : public ITfEditSession {
    LONG refs=1;ITfContext* context;
public:
    std::wstring text;
    CompositionReader(ITfContext* value):context(value){context->AddRef();}
    ~CompositionReader(){context->Release();}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid,void** out)override{
        if(!out)return E_POINTER;*out=nullptr;
        if(IsEqualIID(iid,IID_IUnknown)||IsEqualIID(iid,__uuidof(ITfEditSession))){*out=this;AddRef();return S_OK;}return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef()override{return InterlockedIncrement(&refs);}
    ULONG STDMETHODCALLTYPE Release()override{LONG n=InterlockedDecrement(&refs);if(!n)delete this;return n;}
    HRESULT STDMETHODCALLTYPE DoEditSession(TfEditCookie cookie)override{
        ITfContextComposition* compositions=nullptr;IEnumITfCompositionView* items=nullptr;ITfCompositionView* composition=nullptr;ITfRange* range=nullptr;ULONG fetched=0;
        if(SUCCEEDED(context->QueryInterface(__uuidof(ITfContextComposition),(void**)&compositions)) && compositions){
            if(SUCCEEDED(compositions->EnumCompositions(&items)) && items && items->Next(1,&composition,&fetched)==S_OK && composition){
                if(SUCCEEDED(composition->GetRange(&range)) && range){
                    wchar_t buffer[4096]={};ULONG count=0;
                    if(SUCCEEDED(range->GetText(cookie,0,buffer,4095,&count)) && count<4095)text.assign(buffer,count);
                    range->Release();
                }
                composition->Release();
            }
            if(items)items->Release();compositions->Release();
        }
        return S_OK;
    }
};
static std::wstring tsfCompositionText(){
    if(!tm || !queryClientId)return L"";
    ITfDocumentMgr* document=nullptr;ITfContext* context=nullptr;ITfContextView* view=nullptr;HWND hwnd=nullptr;
    if(FAILED(tm->GetFocus(&document)) || !document)return L"";
    document->GetTop(&context);document->Release();if(!context)return L"";
    if(SUCCEEDED(context->GetActiveView(&view)) && view){view->GetWnd(&hwnd);view->Release();}
    if(!hwnd || (hwnd!=editor && GetAncestor(hwnd,GA_ROOT)!=windowHandle)){context->Release();return L"";}
    auto session=new CompositionReader(context);HRESULT result=E_FAIL;
    HRESULT requested=context->RequestEditSession(queryClientId,session,TF_ES_SYNC|TF_ES_READ,&result);
    std::wstring text=SUCCEEDED(requested)&&SUCCEEDED(result)?session->text:L"";
    session->Release();context->Release();return text;
}
static std::vector<std::wstring> wholeCompositionCandidates() {
    HIMC context=ImmGetContext(editor);
    std::wstring composition;std::vector<BYTE> attributes;
    if(context) {
        LONG bytes=ImmGetCompositionStringW(context,GCS_COMPSTR,nullptr,0);
        if(bytes>0 && bytes<8192 && bytes%2==0) {
            composition.resize(bytes/2);
            ImmGetCompositionStringW(context,GCS_COMPSTR,composition.data(),bytes);
            LONG count=ImmGetCompositionStringW(context,GCS_COMPATTR,nullptr,0);
            if(count>0 && count<8192) {
                attributes.resize(count);ImmGetCompositionStringW(context,GCS_COMPATTR,attributes.data(),count);
            }
        }
        ImmReleaseContext(editor,context);
    }
    if(composition.empty() || attributes.size()!=composition.size()) {
        auto text=tsfCompositionText();if(!text.empty()){composition=text;attributes.clear();}
    }
    std::vector<std::wstring> result;
    // TSF/IMM candidate lists may describe only one clause. Never replace a
    // complete input sentence with a clause by itself.
    if(composition.empty())return result;
    result.push_back(composition);
    size_t begin=composition.size(),end=0;
    if(attributes.size()==composition.size())for(size_t n=0;n<attributes.size();n++) {
        if(attributes[n]==ATTR_TARGET_CONVERTED || attributes[n]==ATTR_TARGET_NOTCONVERTED) {
            begin=std::min(begin,n);end=n+1;
        }
    }
    if(begin<end)for(auto& candidate:queryStrings) {
        auto prefix=composition.substr(0,begin),suffix=composition.substr(end);
        auto comparable=[](std::wstring value) {
            for(auto& c:value)if(c>=0x30a1 && c<=0x30f6)c-=0x60;
            return value;
        };
        auto normalized=comparable(candidate),tail=comparable(suffix);
        // Some IMEs mix full-reading suggestions into a clause candidate list.
        // They already contain the suffix and must not receive it twice.
        if(normalized==comparable(queryReadings[queryReadingIndex]))
            result.push_back(candidate);
        else if(!tail.empty() && normalized.size()>=tail.size() &&
           normalized.compare(normalized.size()-tail.size(),tail.size(),tail)==0)
            result.push_back(prefix+candidate);
        else result.push_back(prefix+candidate+suffix);
        if(result.size()>=11)break;
    }
    return result;
}
static void emitQueryResult(bool partial) {
    auto normalized=reading::convert(hangulInput);
    printf("{\"id\":%u,\"source\":%s,\"kana\":%s,\"partial\":%s,\"candidates\":[",
           queryId,json(hangulInput).c_str(),json(normalized.kana).c_str(),partial?"true":"false");
    for(size_t n=0;n<mergedCandidates.size();n++)printf("%s%s",n?",":"",json(mergedCandidates[n]).c_str());
    printf("],\"readings\":[");
    for(size_t n=0;n<mergedReadings.size();n++)printf("%s%s",n?",":"",json(mergedReadings[n]).c_str());
    printf("],\"kana_variants\":%s,\"queried_readings\":%u,\"document_focus\":%s,\"composition_set\":%s,\"conversion_requested\":%s}\n",
           kanaAlternativesJson(normalized).c_str(),(unsigned)(queryReadingIndex+1),queryDocument?"true":"false",
           queryComposition?"true":"false",queryConverted?"true":"false");fflush(stdout);
}
static void tick() {
    // TSF/IMM calls can pump COM/window messages. A nested WM_TIMER must not
    // mutate the request/reading vectors used by the outer conversion.
    if(tickRunning)return;
    struct TickGuard{TickGuard(){tickRunning=true;}~TickGuard(){tickRunning=false;}} guard;
    // 80 ms per tick; wait for focus/IME initialization before typing.
    step++;
    if(queryLive) {
        if(!queryInitialized && step>=2) {
            SendMessageW(editor,WM_SETFOCUS,0,0);
            activateInputLanguage(lang);
            ITfDocumentMgr* document=nullptr;tm->GetFocus(&document);
            queryDocument=document!=nullptr;if(document) document->Release();
            queryInitialized=true;
            if(queryServer) {printf("{\"event\":\"ready\"}\n");fflush(stdout);}
        }
        if(queryServer) {
            DWORD available=0;
            HANDLE input=GetStdHandle(STD_INPUT_HANDLE);
            if(!PeekNamedPipe(input,nullptr,0,nullptr,&available,nullptr)) {DestroyWindow(windowHandle);return;}
            if(available) {
                char buffer[8192];DWORD received=0;
                if(ReadFile(input,buffer,std::min<DWORD>(available,sizeof buffer),&received,nullptr)) queryInput.append(buffer,received);
                // A valid 4,096-codepoint request can contain 32,768 hex
                // digits plus its header. Bound the frame, not the word.
                if(queryInput.size()>65536) {event("query_frame_overflow",E_INVALIDARG);DestroyWindow(windowHandle);return;}
                size_t end;
                while((end=queryInput.find('\n'))!=std::string::npos) {
                    auto command=queryInput.substr(0,end);queryInput.erase(0,end+1);
                    if(command=="QUIT") {DestroyWindow(windowHandle);return;}
                    if(command=="CANCEL") {
                        queryActive=queryCollect=false;gotCandidates=false;queryStrings.clear();
                        HIMC context=ImmGetContext(editor);
                        if(context){ImmNotifyIME(context,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,context);}
                        SetWindowTextW(editor,L"");continue;
                    }
                    unsigned id=0;char hex[32769]={};
                    if(sscanf(command.c_str(),"QUERY %u %32768s",&id,hex)==2) {
                        auto input=fromHex(hex);auto result=reading::convert(input);
                        if(!result.ok()) {
                            queryActive=false;queryCollect=false;queryStrings.clear();
                            HIMC context=ImmGetContext(editor);
                            if(context){ImmNotifyIME(context,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,context);}
                            printf("{\"id\":%u,\"source\":%s,\"kana\":%s,\"error\":%s,\"candidates\":[]}\n",id,json(input).c_str(),json(result.kana).c_str(),json(result.error).c_str());fflush(stdout);continue;
                        }
                        HIMC c=ImmGetContext(editor);
                        if(c) {ImmNotifyIME(c,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,c);}
                        SetWindowTextW(editor,L"");
                        hangulInput=input;queryId=id;gotCandidates=false;queryStrings.clear();
                        queryReadings=result.alternatives;queryReadingIndex=0;mergedCandidates.clear();mergedReadings.clear();queryCollect=false;
                        activeElement=DWORD(-1);queryComposition=queryConverted=false;
                        queryActive=true;queryRetries=0;step=2;
                    }
                }
            }
            if(!queryActive || !queryInitialized) return;
        }
        if(step==(queryServer?3:4)) {
            auto result=reading::convert(hangulInput);
            auto kana=queryServer?queryReadings[queryReadingIndex]:result.kana;
            gotCandidates=false;queryStrings.clear();
            HIMC c=ImmGetContext(editor);
            queryComposition=ImmSetCompositionStringW(c,SCS_SETSTR,kana.data(),(DWORD)kana.size()*2,nullptr,0)!=FALSE;
            event("set_composition",queryComposition?S_OK:E_FAIL);
            ImmReleaseContext(editor,c);
        }
        if(step==(queryServer?4:6)) {
            queryStrings.clear();gotCandidates=false;queryCollect=false;
            HIMC c=ImmGetContext(editor);queryConverted=ImmNotifyIME(c,NI_COMPOSITIONSTR,CPS_CONVERT,0)!=FALSE;ImmReleaseContext(editor,c);
            queryCollect=true;
        }
        if(step>=(queryServer?5:7) && (queryServer || !gotCandidates)) {
            HIMC c=ImmGetContext(editor);
            DWORD bytes=c?ImmGetCandidateListW(c,0,nullptr,0):0;
            if(bytes>=sizeof(CANDIDATELIST) && bytes<1024*1024) {
                std::vector<BYTE> buffer(bytes);
                auto list=(CANDIDATELIST*)buffer.data();
                if(ImmGetCandidateListW(c,0,list,bytes)) {
                    if(queryServer)queryStrings.clear();
                    for(DWORD i=0;i<list->dwCount && i<200 && 24+i*4+4<=bytes;i++) {
                        DWORD offset=list->dwOffset[i];
                        if(offset>=bytes || offset%2) continue;
                        auto text=(const wchar_t*)(buffer.data()+offset);
                        size_t maximum=(bytes-offset)/2,length=0;
                        while(length<maximum && text[length]) length++;
                        if(length && length<maximum) queryStrings.emplace_back(text,length);
                    }
                    gotCandidates=!queryStrings.empty();lastQueryUpdate=GetTickCount();
                }
            }
            if(c) ImmReleaseContext(editor,c);
        }
        // A cold TIP can acknowledge composition before its dictionary is ready.
        // Retry once after pumping messages; never delay the normal warm path.
        if(queryServer && step==14 && (!gotCandidates || !queryConverted) && queryRetries==0) {
            queryRetries++;
            HIMC c=ImmGetContext(editor);
            if(c) {ImmNotifyIME(c,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,c);}
            SetWindowTextW(editor,L"");
            SendMessageW(editor,WM_SETFOCUS,0,0);activateInputLanguage(lang);
            gotCandidates=false;queryStrings.clear();activeElement=DWORD(-1);
            queryComposition=queryConverted=false;step=2;return;
        }
        auto complete=queryServer && step>=5?wholeCompositionCandidates():std::vector<std::wstring>{};
        bool convertedText=false;
        for(auto& value:complete)if(!value.empty() && value!=queryReadings[queryReadingIndex])convertedText=true;
        bool serverReady=(step>=5 && convertedText) || (step>=(queryReadingIndex==0?60:25) && gotCandidates && queryConverted) || step>=160;
        if(queryServer?serverReady:((step>=12 && gotCandidates && GetTickCount()-lastQueryUpdate>=60)||step>=100)) {
            if(queryServer) {
                for(auto& candidate:complete) {
                    if(std::find(mergedCandidates.begin(),mergedCandidates.end(),candidate)==mergedCandidates.end()) {
                        // One prolific reading must not consume the entire
                        // result budget before a later pronunciation is seen.
                        if(mergedCandidates.size()==200 &&
                           std::find(mergedReadings.begin(),mergedReadings.end(),queryReadings[queryReadingIndex])==mergedReadings.end()) {
                            for(size_t i=mergedReadings.size();i>1;i--) {
                                auto& reading=mergedReadings[i-1];
                                if(std::count(mergedReadings.begin(),mergedReadings.end(),reading)>1) {
                                    mergedCandidates.erase(mergedCandidates.begin()+i-1);
                                    mergedReadings.erase(mergedReadings.begin()+i-1);break;
                                }
                            }
                        }
                        if(mergedCandidates.size()==200)continue;
                        mergedCandidates.push_back(candidate);
                        mergedReadings.push_back(queryReadings[queryReadingIndex]);
                    }
                }
                bool more=queryReadingIndex+1<queryReadings.size();
                emitQueryResult(more);
                queryCollect=false;
                HIMC c=ImmGetContext(editor);
                if(c){ImmNotifyIME(c,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,c);}
                SetWindowTextW(editor,L"");gotCandidates=false;queryStrings.clear();activeElement=DWORD(-1);
                if(more) {queryReadingIndex++;queryComposition=queryConverted=false;queryRetries=0;step=2;}
                else queryActive=false;
                return;
            }
            auto result=reading::convert(hangulInput);
            printf("{\"id\":%u,\"source\":%s,\"kana\":%s,\"candidates\":[",queryId,json(hangulInput).c_str(),json(result.kana).c_str());
            std::vector<std::wstring> unique;
            for(auto& str:queryStrings) {
                bool seen=false;for(auto& old:unique) if(old==str) seen=true;
                if(!seen) unique.push_back(str);
            }
            for(size_t i=0;i<unique.size();i++) printf("%s%s",i?",":"",json(unique[i]).c_str());
            printf("],\"kana_variants\":%s,\"document_focus\":%s,\"composition_set\":%s,\"conversion_requested\":%s}\n",kanaAlternativesJson(result).c_str(),queryDocument?"true":"false",queryComposition?"true":"false",queryConverted?"true":"false");fflush(stdout);
            HIMC c=ImmGetContext(editor);
            if(c) {ImmNotifyIME(c,NI_COMPOSITIONSTR,CPS_CANCEL,0);ImmReleaseContext(editor,c);}
            if(queryServer) {queryActive=false;gotCandidates=false;queryStrings.clear();}
            else DestroyWindow(windowHandle);
        }
        return;
    }
    if(inputAborted) {finish();return;}
    if(step==12) {
        // RichEdit can restore the previous input service when it gains focus.
        // Activate the selected default TIP AFTER its document owns focus.
        activateInputLanguage(!automatic && GetFocus()==sourceEditor?0x0412:lang);
        ITfDocumentMgr* document=nullptr;
        HRESULT result=tm->GetFocus(&document);
        event(document?"document_focus_present":"document_focus_missing",result);
        if(document) document->Release();
    }
    if(step==16) {
        HWND field=GetFocus();
        HIMC c=ImmGetContext(field);
        if(c) {
            ImmSetOpenStatus(c,TRUE);
            ImmSetConversionStatus(c,field==sourceEditor?IME_CMODE_NATIVE:IME_CMODE_NATIVE|IME_CMODE_FULLSHAPE|IME_CMODE_ROMAN,0);
            DWORD conversion=0,sentence=0;ImmGetConversionStatus(c,&conversion,&sentence);
            if(logFile) fprintf(logFile,"{\"event\":\"ime_state\",\"language\":%u,\"open\":%s,\"conversion\":%lu}\n",LOWORD((ULONG_PTR)GetKeyboardLayout(0)),ImmGetOpenStatus(c)?"true":"false",conversion);
            ImmReleaseContext(field,c);
        }
        if(hangulTest && !prepareConversion(buttonTest)) {actionsOK=false;inputAborted=true;}
        if(!automatic) KillTimer(windowHandle,1);
    }
    if(!automatic) return;
    if(!buttonTest && step>=20 && step<20+(int)romaji.size()) {
        wchar_t c=romaji[step-20];
        readingKey(c);
    }
    int end=20+(int)romaji.size();
    if(!buttonTest && (step==end+5 || step==end+9)) key(VK_SPACE);
    if(step==end+21 && activeElement!=DWORD(-1)) {snapshot(activeElement,"before_navigation");screenshot();}
    if(step==end+24) {
        if(useBehavior && activeElement!=DWORD(-1)) {HRESULT h=controlCandidate(false,false);event("behavior_select",h);actionsOK=actionsOK&&SUCCEEDED(h);}
        else key(VK_DOWN);
    }
    if(step==end+30 && activeElement!=DWORD(-1)) snapshot(activeElement,"after_navigation");
    if(step==end+34) {
        if((useBehavior||abortCandidate) && activeElement!=DWORD(-1)) {HRESULT h=controlCandidate(!cancelTest,cancelTest);event(cancelTest?"behavior_abort":"behavior_finalize",h);actionsOK=actionsOK&&SUCCEEDED(h);}
        else key(cancelTest?VK_ESCAPE:VK_RETURN);
    }
    // Abort closes the candidate UI; Escape also cancels remaining composition.
    if(cancelTest && (step==end+37 || step==end+40)) key(VK_ESCAPE);
    if(step==end+44) finish();
}
static LRESULT CALLBACK proc(HWND hwnd,UINT msg,WPARAM w,LPARAM l) {
    if(msg==WM_GETMINMAXINFO) {auto info=(MINMAXINFO*)l;info->ptMinTrackSize.x=760;info->ptMinTrackSize.y=680;return 0;}
    if(msg==WM_TIMER) {if(w==2) feedTick();else tick();return 0;}
    if(msg==WM_COMMAND) {
        if(LOWORD(w)==5001 && HIWORD(w)==EN_CHANGE) {updateReading();return 0;}
        if(LOWORD(w)==5003 && (HIWORD(w)==BN_CLICKED || !l)) {prepareConversion(true);return 0;}
        if(HIWORD(w)==EN_SETFOCUS) {PostMessageW(hwnd,WM_APP+9,LOWORD(w)==5001?0x0412:lang,0);}
    }
    if(msg==WM_APP+9) {if(!automatic) activateInputLanguage(GetFocus()==sourceEditor?0x0412:lang);return 0;}
    if(msg==WM_SETFOCUS && sourceEditor) {SetFocus(automatic?editor:sourceEditor);return 0;}
    if(msg==WM_DESTROY) {PostQuitMessage(0);return 0;}
    return DefWindowProcW(hwnd,msg,w,l);
}
static int hostMain(int argc,wchar_t** argv) {
    SetDllDirectoryW(nullptr);  // Do not inherit a frozen Python host's DLL directory.
    if(argc>=2 && (!wcscmp(argv[1],L"--watch-input") || !wcscmp(argv[1],L"--watch-roman"))) {
        inlineRoman=!wcscmp(argv[1],L"--watch-roman");
        return runInlineWatcher(argc==4 && !wcscmp(argv[2],L"--owner-pid")?(DWORD)wcstoul(argv[3],nullptr,10):0);
    }
    if(argc>=3 && !wcscmp(argv[1],L"--normalize")) {
        for(int i=2;i<argc;i++) {
            auto r=reading::convert(argv[i]);
            printf("{\"source\":%s,\"kana\":%s,\"kana_variants\":%s,\"romaji\":%s,\"error\":%s}\n",json(argv[i]).c_str(),json(r.kana).c_str(),kanaAlternativesJson(r).c_str(),json(r.romaji).c_str(),json(r.error).c_str());
        }
        return 0;
    }
    const wchar_t* logPath=nullptr;
    for(int i=1;i<argc;i++) {
        if(!wcscmp(argv[i],L"--auto")) automatic=true;
        else if(!wcscmp(argv[i],L"--query-live") && i+1<argc) {queryLive=true;automatic=true;hangulInput=argv[++i];}
        else if(!wcscmp(argv[i],L"--query-server")) {queryLive=true;queryServer=true;automatic=true;}
        else if(!wcscmp(argv[i],L"--shared-desktop")) sharedQueryDesktop=true;
        else if(!wcscmp(argv[i],L"--diagnostic-ignore-layout-cache")) ignoreLayoutCache=true;
        else if(!wcscmp(argv[i],L"--button-test")) buttonTest=true;
        else if(!wcscmp(argv[i],L"--behavior")) useBehavior=true;
        else if(!wcscmp(argv[i],L"--cancel")) cancelTest=true;
        else if(!wcscmp(argv[i],L"--abort")) {cancelTest=true;abortCandidate=true;}
        else if(!wcscmp(argv[i],L"--screenshot") && i+1<argc) screenshotPath=argv[++i];
        else if(!wcscmp(argv[i],L"--native-ui")) nativeUI=true;
        else if(!wcscmp(argv[i],L"--romaji") && i+1<argc) romaji=argv[++i];
        else if(!wcscmp(argv[i],L"--hangul") && i+1<argc) {hangulInput=argv[++i];hangulTest=true;}
        else if(!wcscmp(argv[i],L"--pinyin")) {lang=0x0804;romaji=L"nihao";}
        else if(!wcscmp(argv[i],L"--log") && i+1<argc) logPath=argv[++i];
    }
    if(logPath) logFile=_wfopen(logPath,L"wb");
    if(queryLive) {
        auto result=reading::convert(hangulInput);
        if(!queryServer && !result.ok()) {
            printf("{\"source\":%s,\"kana\":%s,\"error\":%s,\"candidates\":[]}\n",json(hangulInput).c_str(),json(result.kana).c_str(),json(result.error).c_str());
            if(logFile) fclose(logFile);
            return 0;
        }
        // The query document lives on a private, undisplayed desktop. It can
        // own TSF document focus without activating a window in the user's app.
        std::wstring desktopName=L"LexiftIME_"+std::to_wstring(GetCurrentProcessId());
        HDESK desktop=sharedQueryDesktop?nullptr:CreateDesktopW(desktopName.c_str(),nullptr,nullptr,0,
            DESKTOP_CREATEWINDOW|DESKTOP_CREATEMENU|DESKTOP_READOBJECTS|DESKTOP_WRITEOBJECTS|DESKTOP_ENUMERATE|DESKTOP_HOOKCONTROL,nullptr);
        if(!sharedQueryDesktop && (!desktop || !SetThreadDesktop(desktop))) {
            event("query_desktop_failed",HRESULT_FROM_WIN32(GetLastError()));
            if(desktop) CloseDesktop(desktop);
            return 7;
        }
    }
    HRESULT init=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
    event("initialize_com",init);
    if(FAILED(init)) return 2;
    HRESULT result=CoCreateInstance(threadCLSID,nullptr,CLSCTX_INPROC_SERVER,__uuidof(ITfThreadMgrEx),(void**)&tm);
    event("thread_manager",result);
    if(FAILED(result)) {CoUninitialize();return 2;}
    TfClientId client;
    result=tm->ActivateEx(&client,0x4); // TF_TMAE_UIELEMENTENABLEDONLY
    if(SUCCEEDED(result))queryClientId=client;
    event("activate_uiless",result);
    if(FAILED(result)) {tm->Release();CoUninitialize();return 2;}
    tm->QueryInterface(__uuidof(ITfUIElementMgr),(void**)&ui);
    tm->QueryInterface(__uuidof(ITfSource),(void**)&source);
    if(!ui || !source) {event("missing_tsf_interfaces",E_NOINTERFACE);return 2;}
    Sink* sink=new Sink;
    result=source->AdviseSink(__uuidof(ITfUIElementSink),sink,&cookie);
    sink->Release();event("advise_sink",result);
    ITfInputProcessorProfiles* profiles=nullptr;
    CoCreateInstance(profilesCLSID,nullptr,CLSCTX_INPROC_SERVER,__uuidof(ITfInputProcessorProfiles),(void**)&profiles);
    HKL old=GetKeyboardLayout(0);
    LANGID oldLang=0;
    if(profiles)profiles->GetCurrentLanguage(&oldLang);
    bool profileActivated=activateProfile(profiles,(LANGID)lang);
    int layoutCount=ignoreLayoutCache?0:GetKeyboardLayoutList(0,nullptr);
    std::vector<HKL> layouts(layoutCount>0?layoutCount:0);
    int loaded=layouts.empty()?0:GetKeyboardLayoutList((int)layouts.size(),layouts.data());
    layouts.resize(loaded>0?std::min<size_t>(loaded,layouts.size()):0);
    bool found=false;
    for(auto layout:layouts) if(LOWORD((ULONG_PTR)layout)==lang) {ActivateKeyboardLayout(layout,0);found=true;break;}
    if(!found){
        // Ask Windows for the existing Japanese layout without KLF_ACTIVATE,
        // KLF_REORDER or registry changes. TSF profile activation is preferred.
        wchar_t klid[9]={};swprintf(klid,9,L"%08x",lang);
        HKL loadedLayout=LoadKeyboardLayoutW(klid,0);
        if(loadedLayout && LOWORD((ULONG_PTR)loadedLayout)==lang){ActivateKeyboardLayout(loadedLayout,0);found=true;}
        event("load_query_layout",found?S_OK:HRESULT_FROM_WIN32(GetLastError()));
    }
    event(found?"layout_found":"layout_missing",found?S_OK:E_FAIL);
    // GetKeyboardLayoutList is a cache of loaded HKLs, not the list of
    // installed TSF profiles. A modern Japanese TIP can work without an HKL
    // in that cache, especially in a fresh private desktop on another PC.
    if(!found && !profileActivated) {event("japanese_profile_unavailable",E_FAIL);if(profiles){if(oldLang)profiles->ChangeCurrentLanguage(oldLang);profiles->Release();} source->UnadviseSink(cookie);source->Release();ui->Release();tm->Deactivate();tm->Release();CoUninitialize();return 3;}
    HMODULE rich=LoadLibraryW(L"msftedit.dll");
    WNDCLASSW wc={};wc.lpfnWndProc=proc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"Lexift08ImeLab";wc.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);wc.hCursor=LoadCursorW(nullptr,IDC_ARROW);
    RegisterClassW(&wc);
    windowHandle=CreateWindowExW(queryLive?WS_EX_NOACTIVATE|WS_EX_TOOLWINDOW:0,wc.lpszClassName,L"Lexift · 한글 발음으로 일본어 입력",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,760,680,nullptr,nullptr,wc.hInstance,nullptr);
    HFONT font=nullptr;
    if(queryLive) {
        editor=CreateWindowExW(0,L"RICHEDIT50W",L"",WS_CHILD|ES_AUTOHSCROLL,0,0,128,32,windowHandle,(HMENU)5004,wc.hInstance,nullptr);
        SendMessageW(editor,EM_SETEDITSTYLE,SES_USECTF,SES_USECTF);
    } else {
    HWND hint=CreateWindowExW(0,L"STATIC",L"한글 발음 → 일본어 독음 → IME 후보",WS_CHILD|WS_VISIBLE,20,14,700,28,windowHandle,nullptr,wc.hInstance,nullptr);
    sourceEditor=CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|ES_AUTOHSCROLL,20,50,700,36,windowHandle,(HMENU)5001,wc.hInstance,nullptr);
    SendMessageW(sourceEditor,EM_SETCUEBANNER,TRUE,(LPARAM)L"와타시 · 니혼고 · 센세이 · 갓코우");
    SendMessageW(sourceEditor,EM_LIMITTEXT,256,0);
    previousEditProc=(WNDPROC)SetWindowLongPtrW(sourceEditor,GWLP_WNDPROC,(LONG_PTR)readingProc);
    HWND readingLabel=CreateWindowExW(0,L"STATIC",L"독음 확인 / 수정",WS_CHILD|WS_VISIBLE,20,98,700,25,windowHandle,nullptr,wc.hInstance,nullptr);
    readingEditor=CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|ES_AUTOHSCROLL,20,128,530,36,windowHandle,(HMENU)5002,wc.hInstance,nullptr);
    SendMessageW(readingEditor,EM_LIMITTEXT,256,0);
    SetWindowLongPtrW(readingEditor,GWLP_WNDPROC,(LONG_PTR)readingProc);
    convertButton=CreateWindowExW(0,L"BUTTON",L"일본어 변환",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_PUSHBUTTON,566,128,154,36,windowHandle,(HMENU)5003,wc.hInstance,nullptr);
    EnableWindow(convertButton,FALSE);
    noteLabel=CreateWindowExW(0,L"STATIC",L"발음을 적으면 독음을 미리 보여줍니다. 확인 후 변환하세요.",WS_CHILD|WS_VISIBLE,20,176,700,54,windowHandle,nullptr,wc.hInstance,nullptr);
    HWND editorLabel=CreateWindowExW(0,L"STATIC",L"일본어 입력 / 확정 결과 (로마자 직접 입력도 가능)",WS_CHILD|WS_VISIBLE,20,234,700,28,windowHandle,nullptr,wc.hInstance,nullptr);
    editor=CreateWindowExW(WS_EX_CLIENTEDGE,L"RICHEDIT50W",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|ES_AUTOHSCROLL,20,267,700,38,windowHandle,(HMENU)5004,wc.hInstance,nullptr);
    SendMessageW(editor,EM_SETEDITSTYLE,SES_USECTF,SES_USECTF);
    previousJapaneseProc=(WNDPROC)SetWindowLongPtrW(editor,GWLP_WNDPROC,(LONG_PTR)japaneseProc);
    outputLabel=CreateWindowExW(0,L"STATIC",L"변환 후보 · 방향키로 선택, Enter로 확정, Esc로 취소",WS_CHILD|WS_VISIBLE,20,323,700,290,windowHandle,nullptr,wc.hInstance,nullptr);
    font=CreateFontW(-20,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Yu Gothic UI");
    for(HWND h:{hint,sourceEditor,readingLabel,readingEditor,convertButton,noteLabel,editorLabel,editor,outputLabel}) SendMessageW(h,WM_SETFONT,(WPARAM)font,TRUE);
    }
    if(hangulTest) SetWindowTextW(sourceEditor,hangulInput.c_str());
    if(!editor) {event("editor_creation_failed",HRESULT_FROM_WIN32(GetLastError()));return 2;}
    if(!queryLive) ShowWindow(windowHandle,SW_SHOW);
    // Initial activation only; never reclaim focus while a test is typing.
    DWORD foregroundThread=GetWindowThreadProcessId(GetForegroundWindow(),nullptr);
    DWORD thisThread=GetCurrentThreadId();
    BOOL attached=!queryLive && foregroundThread!=thisThread && AttachThreadInput(thisThread,foregroundThread,TRUE);
    if(!queryLive) SetForegroundWindow(windowHandle);
    SetFocus(automatic?editor:sourceEditor);
    if(attached) AttachThreadInput(thisThread,foregroundThread,FALSE);
    event("host_ready");
    SetTimer(windowHandle,1,queryServer?10:queryLive?25:80,nullptr);
    MSG message;
    while(GetMessageW(&message,nullptr,0,0)>0) {
        if(message.message==WM_KEYDOWN && message.wParam==VK_TAB &&
           !(GetFocus()==editor && activeElement!=DWORD(-1)) && IsDialogMessageW(windowHandle,&message)) continue;
        TranslateMessage(&message);DispatchMessageW(&message);
    }
    if(cookie!=TF_INVALID_COOKIE) source->UnadviseSink(cookie);
    source->Release();ui->Release();tm->Deactivate();tm->Release();
    if(profiles) {if(oldLang)profiles->ChangeCurrentLanguage(oldLang);profiles->Release();}
    if(old) ActivateKeyboardLayout(old,0);
    if(font) DeleteObject(font);
    if(rich) FreeLibrary(rich);
    CoUninitialize();
    if(logFile) fclose(logFile);
    return queryServer?0:automatic?(gotCandidates&&!inputAborted&&actionsOK?0:4):0;
}
static LONG CALLBACK recordNativeFault(EXCEPTION_POINTERS* details){
    if(details && details->ExceptionRecord && details->ExceptionRecord->ExceptionCode==EXCEPTION_ILLEGAL_INSTRUCTION){
        void* address=details->ExceptionRecord->ExceptionAddress;HMODULE module=nullptr;wchar_t path[1024]={};
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)address,&module);
        if(module)GetModuleFileNameW(module,path,1024);
        const wchar_t* name=wcsrchr(path,L'\\');name=name?name+1:path;
        fprintf(stderr,"native_fault code=0x%08lX module=%ls offset=0x%llX\n",details->ExceptionRecord->ExceptionCode,name,
                (unsigned long long)((ULONG_PTR)address-(ULONG_PTR)module));fflush(stderr);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
    AddVectoredExceptionHandler(1,recordNativeFault);
    int argc=0;
    auto argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    if(!argv) return 2;
    int result=hostMain(argc,argv);LocalFree(argv);return result;
}
