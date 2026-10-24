#include <windows.h>
#include <string>
static LRESULT CALLBACK windowProc(HWND h,UINT m,WPARAM w,LPARAM l) {
    if(m==WM_CLOSE) {DestroyWindow(h);return 0;}
    if(m==WM_DESTROY) {PostQuitMessage(0);return 0;}
    return DefWindowProcW(h,m,w,l);
}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
    wchar_t own[32768];GetModuleFileNameW(nullptr,own,32768);
    std::wstring folder=own;folder=folder.substr(0,folder.find_last_of(L"\\/"));
    std::wstring command=L"\"C:\\Users\\Neko4K\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe\" -B \""+folder+L"\\composition_probe.py\"";
    STARTUPINFOW start={sizeof start};PROCESS_INFORMATION process={};
    if(!CreateProcessW(nullptr,command.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,folder.c_str(),&start,&process)) return 1;
    CloseHandle(process.hThread);
    WNDCLASSW type={};type.hInstance=GetModuleHandleW(nullptr);type.lpfnWndProc=windowProc;type.lpszClassName=L"LexiftDesktopTest";type.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);RegisterClassW(&type);
    HWND window=CreateWindowW(type.lpszClassName,L"Lexift composition launcher",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,330,100,nullptr,nullptr,type.hInstance,nullptr);
    CreateWindowW(L"STATIC",L"다른 앱에서 한글 발음 입력을 시험 중입니다.",WS_CHILD|WS_VISIBLE,12,12,310,30,window,nullptr,type.hInstance,nullptr);
    ShowWindow(window,SW_SHOWNOACTIVATE);
    MSG message;
    while(WaitForSingleObject(process.hProcess,50)==WAIT_TIMEOUT) {
        while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)) {TranslateMessage(&message);DispatchMessageW(&message);}
    }
    DestroyWindow(window);CloseHandle(process.hProcess);return 0;
}
