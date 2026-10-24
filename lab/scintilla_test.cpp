#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <string>
#include "native_edit_adapter.h"
static HWND editor;
static void configure(int mode) {
    SendMessageW(editor,2171,FALSE,0);
    SendMessageW(editor,2037,65001,0); // SCI_SETCODEPAGE
    SendMessageW(editor,2571,0,0); // SCI_CLEARSELECTIONS
    SendMessageW(editor,2422,0,0); // SC_SEL_STREAM
    std::string text=mode==8?u8"첫 줄 😀\r\n앞 문장 니하오 뒤 문장":u8"앞 😀 문장 니하오 뒤 문장";
    auto position=text.find(u8"니하오")+std::string(u8"니하오").size();
    if(mode==1)text.replace(text.find(u8"니하오"),9,u8"셰셰셰");
    SendMessageW(editor,2181,0,(LPARAM)text.c_str()); // local pointer only
    SendMessageW(editor,2160,position,position);
    if(mode==2)SendMessageW(editor,2171,TRUE,0);
    if(mode==3) {SendMessageW(editor,2563,TRUE,0);SendMessageW(editor,2573,0,0);}
    if(mode==4)SendMessageW(editor,2422,1,0);
    if(mode==5)SendMessageW(editor,2037,949,0);
    if(mode==6)SendMessageW(editor,2160,position-3,position-3);
    if(mode==7)SendMessageW(editor,2580,0,2);
}
static LRESULT CALLBACK proc(HWND w,UINT m,WPARAM p,LPARAM l) {
    if(m==WM_APP+1) {configure((int)p);return 1;}
    return DefWindowProcW(w,m,p,l);
}
static DWORD WINAPI input(void* thread) {
    char c;DWORD n;ReadFile(GetStdHandle(STD_INPUT_HANDLE),&c,1,&n,nullptr);
    PostThreadMessageW((DWORD)(ULONG_PTR)thread,WM_QUIT,0,0);return 0;
}
static int fixture() {
    if(!LoadLibraryW(L"C:\\Program Files (x86)\\Notepad++\\SciLexer.dll"))return 2;
    WNDCLASSW wc={};wc.lpfnWndProc=proc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"LexiftScintillaFixture";
    RegisterClassW(&wc);
    HWND root=CreateWindowW(wc.lpszClassName,L"Lexift Scintilla fixture",WS_OVERLAPPEDWINDOW,0,0,650,400,nullptr,nullptr,wc.hInstance,nullptr);
    editor=CreateWindowW(L"Scintilla",L"",WS_CHILD,0,0,600,300,root,nullptr,wc.hInstance,nullptr);
    if(!editor)return 3;
    configure(0);
    printf("%llu %llu\n",(unsigned long long)(ULONG_PTR)root,(unsigned long long)(ULONG_PTR)editor);fflush(stdout);
    MSG message;PeekMessageW(&message,nullptr,0,0,PM_NOREMOVE);
    CloseHandle(CreateThread(nullptr,0,input,(void*)(ULONG_PTR)GetCurrentThreadId(),0,nullptr));
    while(GetMessageW(&message,nullptr,0,0)>0) {TranslateMessage(&message);DispatchMessageW(&message);}
    DestroyWindow(root);return 0;
}
static int tests(const wchar_t* path) {
    SECURITY_ATTRIBUTES sa={sizeof sa,nullptr,TRUE};HANDLE ir,iw,orr,ow;
    CreatePipe(&ir,&iw,&sa,0);CreatePipe(&orr,&ow,&sa,0);
    SetHandleInformation(iw,HANDLE_FLAG_INHERIT,0);SetHandleInformation(orr,HANDLE_FLAG_INHERIT,0);
    STARTUPINFOW si={sizeof si};si.dwFlags=STARTF_USESTDHANDLES;si.hStdInput=ir;si.hStdOutput=ow;si.hStdError=ow;
    PROCESS_INFORMATION pi={};std::wstring command=L"\""+std::wstring(path)+L"\" --fixture";
    if(!CreateProcessW(nullptr,command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW,nullptr,nullptr,&si,&pi))return 4;
    CloseHandle(ir);CloseHandle(ow);CloseHandle(pi.hThread);
    std::string line;char c;DWORD n;while(ReadFile(orr,&c,1,&n,nullptr)&&n) {if(c=='\n')break;line+=c;}
    unsigned long long rootValue=0,editValue=0;
    if(sscanf(line.c_str(),"%llu %llu",&rootValue,&editValue)!=2)return 5;
    HWND root=(HWND)(ULONG_PTR)rootValue,control=(HWND)(ULONG_PTR)editValue;
    int passed=0,failed=0;auto check=[&](const char* label,bool ok) {printf("{\"test\":\"%s\",\"passed\":%s}\n",label,ok?"true":"false");if(ok)passed++;else failed++;};
    NativeEditSnapshot base;DWORD_PTR answer=0;
    check("real 32-bit Scintilla read from 64-bit host",readNativeEdit(root,control,base)&&base.scintilla&&base.token==L"니하오");
    check("UTF8 byte selection after emoji",base.end-base.start==9&&selectNativeEdit(base));
    editMessage(root,WM_APP+1,1,0,answer);
    check("changed word refuses stale selection",!selectNativeEdit(base));
    const char* labels[]={"read only","multiple selections","rectangle selection","non UTF8 codepage","moved caret","virtual space"};
    for(int mode=2;mode<=7;mode++) {
        editMessage(root,WM_APP+1,mode,0,answer);NativeEditSnapshot value;
        bool valid=readNativeEdit(root,control,value);
        check(labels[mode-2],mode==6?(valid&&!sameNativeEdit(base,value)):!valid);
    }
    editMessage(root,WM_APP+1,8,0,answer);NativeEditSnapshot multiline;
    check("multiline UTF8 document",readNativeEdit(root,control,multiline)&&multiline.token==L"니하오"&&selectNativeEdit(multiline));
    WriteFile(iw,"q",1,&n,nullptr);CloseHandle(iw);WaitForSingleObject(pi.hProcess,3000);CloseHandle(pi.hProcess);CloseHandle(orr);
    printf("{\"passed\":%d,\"failed\":%d,\"cross_process\":true,\"cross_bitness\":true}\n",passed,failed);
    return failed?1:0;
}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
    int argc=0;auto argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    int result=argc>1&&!wcscmp(argv[1],L"--fixture")?fixture():argc>1?tests(argv[1]):6;
    LocalFree(argv);return result;
}
