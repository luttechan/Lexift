// Real cross-process controls, with no typing or focus changes in user apps.
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <richedit.h>
#include <stdio.h>
#include <string>
#include <vector>
#include "native_edit_adapter.h"

static LRESULT CALLBACK fixtureProc(HWND window,UINT message,WPARAM w,LPARAM l) {
    if(message==WM_APP+6) {Sleep(700);return 0;}
    return DefWindowProcW(window,message,w,l);
}
static DWORD WINAPI fixtureInput(void* thread) {
    char c;DWORD n;
    ReadFile(GetStdHandle(STD_INPUT_HANDLE),&c,1,&n,nullptr);
    PostThreadMessageW((DWORD)(ULONG_PTR)thread,WM_QUIT,0,0);return 0;
}
static int fixture() {
    WNDCLASSW wc={};wc.lpfnWndProc=fixtureProc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"LexiftAdapterFixture";
    RegisterClassW(&wc);
    HWND root=CreateWindowW(wc.lpszClassName,L"Lexift adapter fixture",WS_OVERLAPPEDWINDOW,0,0,600,400,nullptr,nullptr,wc.hInstance,nullptr);
    LoadLibraryW(L"msftedit.dll");
    std::vector<HWND> controls;
    auto add=[&](const wchar_t* name,const std::wstring& text,DWORD style,int caret) {
        HWND edit=CreateWindowW(name,L"",WS_CHILD|style,0,0,300,30,root,nullptr,wc.hInstance,nullptr);
        SetWindowTextW(edit,text.c_str());SendMessageW(edit,EM_SETSEL,caret,caret);controls.push_back(edit);
    };
    add(L"Edit",L"앞 문장 니하오 뒤 문장",0,8);
    add(L"Edit",L"첫 줄\r\n둘째 니하오 끝",ES_MULTILINE,11);
    add(L"RICHEDIT50W",L"앞 문장 와타시",0,8);
    add(L"Edit",L"니하오",ES_PASSWORD,3);
    add(L"Edit",L"니하오",ES_READONLY,3);
    add(L"Edit",L"니하오",0,3);EnableWindow(controls.back(),FALSE);
    add(L"Edit",L"니하오",0,3);SendMessageW(controls.back(),EM_SETSEL,0,3);
    add(L"Edit",L"니하오",0,3);SendMessageW(controls.back(),EM_SETPASSWORDCHAR,L'*',0);
    add(L"STATIC",L"니하오",0,3);
    add(L"Edit",std::wstring(60001,L'가'),0,60001);
    add(L"RICHEDIT50W",L"앞\r\n니하오",ES_MULTILINE,6);
    HWND ansi=CreateWindowA("Edit","plain",WS_CHILD,0,0,300,30,root,nullptr,wc.hInstance,nullptr);controls.push_back(ansi);
    printf("%llu",(unsigned long long)(ULONG_PTR)root);
    for(auto edit:controls)printf(" %llu",(unsigned long long)(ULONG_PTR)edit);
    printf("\n");fflush(stdout);
    MSG message;PeekMessageW(&message,nullptr,0,0,PM_NOREMOVE);
    HANDLE input=CreateThread(nullptr,0,fixtureInput,(void*)(ULONG_PTR)GetCurrentThreadId(),0,nullptr);CloseHandle(input);
    while(GetMessageW(&message,nullptr,0,0)>0) {TranslateMessage(&message);DispatchMessageW(&message);}
    DestroyWindow(root);return 0;
}
static bool readLine(HANDLE pipe,std::string& line) {
    char c;DWORD n;
    while(ReadFile(pipe,&c,1,&n,nullptr)&&n) {if(c=='\n')return true;line+=c;}
    return false;
}
static int tests() {
    SECURITY_ATTRIBUTES security={sizeof security,nullptr,TRUE};HANDLE inputRead,inputWrite,outputRead,outputWrite;
    if(!CreatePipe(&inputRead,&inputWrite,&security,0)||!CreatePipe(&outputRead,&outputWrite,&security,0))return 2;
    SetHandleInformation(inputWrite,HANDLE_FLAG_INHERIT,0);SetHandleInformation(outputRead,HANDLE_FLAG_INHERIT,0);
    wchar_t own[32768];GetModuleFileNameW(nullptr,own,32768);std::wstring command=L"\""+std::wstring(own)+L"\" --fixture";
    STARTUPINFOW startup={sizeof startup};startup.dwFlags=STARTF_USESTDHANDLES;startup.hStdInput=inputRead;startup.hStdOutput=outputWrite;startup.hStdError=outputWrite;
    PROCESS_INFORMATION child={};
    if(!CreateProcessW(nullptr,command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&child))return 3;
    CloseHandle(inputRead);CloseHandle(outputWrite);CloseHandle(child.hThread);
    std::string line;if(!readLine(outputRead,line))return 4;
    std::vector<HWND> handles;const char* pos=line.c_str();char* end;
    while(*pos) {unsigned long long value=strtoull(pos,&end,10);if(end==pos)break;handles.push_back((HWND)(ULONG_PTR)value);pos=end;while(*pos==' ')pos++;}
    if(handles.size()!=13)return 5;
    HWND root=handles[0];int passed=0,failed=0;
    auto check=[&](const char* name,bool success) {printf("{\"test\":\"%s\",\"passed\":%s}\n",name,success?"true":"false");if(success)passed++;else failed++;};
    NativeEditSnapshot edit,multiline,rich;
    check("Edit middle word, preserve surrounding text",readNativeEdit(root,handles[1],edit)&&edit.token==L"니하오"&&edit.start==5&&edit.end==8);
    check("multiline Edit CRLF offsets",readNativeEdit(root,handles[2],multiline)&&multiline.token==L"니하오");
    check("RichEdit50 Unicode",readNativeEdit(root,handles[3],rich)&&rich.token==L"와타시");
    const char* denied[]={"password","read only","disabled","selected text","custom password character","non editor","over 60000 units","ambiguous multiline RichEdit","ANSI editor"};
    for(size_t i=4;i<handles.size();i++) {NativeEditSnapshot blocked;check(denied[i-4],!readNativeEdit(root,handles[i],blocked));}
    NativeEditSnapshot mismatch;
    check("unrelated root rejected",!readNativeEdit(handles[3],handles[1],mismatch));
    DWORD_PTR answer=0;
    editMessage(handles[1],EM_SETSEL,7,7,answer);
    check("moved caret refuses selection",!selectNativeEdit(edit));
    editMessage(handles[1],EM_SETSEL,8,8,answer);
    editMessage(handles[1],WM_SETTEXT,0,(LPARAM)L"앞 문장 니하오 바뀜",answer);
    editMessage(handles[1],EM_SETSEL,8,8,answer);
    check("changed suffix refuses selection",!selectNativeEdit(edit));
    editMessage(handles[1],WM_SETTEXT,0,(LPARAM)L"앞 문장 니하오 뒤 문장",answer);
    editMessage(handles[1],EM_SETSEL,8,8,answer);
    check("only original word selected",selectNativeEdit(edit));
    editMessage(handles[1],EM_SETSEL,8,8,answer);
    {
        auto marked=edit.fullText;marked.insert(edit.end,L" ");
        editMessage(handles[1],WM_SETTEXT,0,(LPARAM)marked.c_str(),answer);
        editMessage(handles[1],EM_SETSEL,edit.end+1,edit.end+1,answer);
        inlineCommitSpace=true;NativeEditSnapshot settled;
        check("exact composition space accepted",readNativeEdit(root,handles[1],settled) && sameNativeAfterCommitSpace(edit,settled));
        bool selected=selectNativeEdit(settled);
        editMessage(handles[1],EM_REPLACESEL,TRUE,(LPARAM)L"日本語",answer);
        DWORD_PTR selection=0;editMessage(handles[1],EM_GETSEL,0,0,selection);
        check("replacement caret stays after Unicode text",selected && LOWORD(selection)==edit.start+3 && HIWORD(selection)==edit.start+3);
        auto changed=settled;changed.fullText+=L"!";
        check("changed document refuses composition replacement",!sameNativeAfterCommitSpace(edit,changed));
        inlineCommitSpace=false;
    }
    PostMessageW(root,WM_APP+6,0,0);Sleep(30);
    ULONGLONG started=GetTickCount64();NativeEditSnapshot hung;
    bool refused=!readNativeEdit(root,handles[1],hung);
    check("hung process bounded timeout",refused&&GetTickCount64()-started<500);
    DWORD n;WriteFile(inputWrite,"q",1,&n,nullptr);CloseHandle(inputWrite);
    WaitForSingleObject(child.hProcess,3000);CloseHandle(child.hProcess);CloseHandle(outputRead);
    printf("{\"passed\":%d,\"failed\":%d,\"cross_process\":true}\n",passed,failed);
    return failed?1:0;
}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
    int argc=0;auto argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    bool child=argc>1&&!wcscmp(argv[1],L"--fixture");LocalFree(argv);
    return child?fixture():tests();
}
