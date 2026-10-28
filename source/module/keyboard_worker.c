/* Minimal authenticated loopback host for the existing native hook state machine.
 * Ordinary keys never enter the socket/message processing thread.
 */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native_hooks.c"

static SOCKET channel=INVALID_SOCKET;
static const char *cap_event[4]={0};
static BOOL nav_running=FALSE;
static const char *names[]={"hotkey","ime","chinese","traditional"};

static BOOL transmit(const char *value) {
    size_t size=strlen(value),sent=0;
    while(sent<size) {int n=send(channel,value+sent,(int)(size-sent),0);if(n<=0)return FALSE;sent+=n;}
    return TRUE;
}
static const char *field(const char *json,const char *key) {
    size_t length=strlen(key);
    const char *p=json;
    while((p=strchr(p,'\"'))) {
        const char *start=++p;BOOL escaped=FALSE;
        while(*p && *p!='\"') {
            if(*p=='\\') {escaped=TRUE;if(!p[1])return NULL;p+=2;}
            else p++;
        }
        if(!*p)return NULL;
        const char *end=p++;
        while(*p==' '||*p=='\t'||*p=='\r'||*p=='\n')p++;
        /* A string value can equal a key: operation="active" is not the
         * active field. Skip complete strings, including escaped quotes. */
        if(*p==':' && !escaped && (size_t)(end-start)==length && !memcmp(start,key,length)) {
            p++;while(*p==' '||*p=='\t'||*p=='\r'||*p=='\n')p++;
            return p;
        }
    }
    return NULL;
}
static BOOL text(const char *json,const char *key,char *out,size_t capacity,const char *fallback) {
    const char *p=field(json,key);
    if(!p) {snprintf(out,capacity,"%s",fallback);return TRUE;}
    if(*p++!='\"')return FALSE;size_t n=0;
    while(*p && *p!='\"') {if(n+1>=capacity || *p=='\\' || (unsigned char)*p<32)return FALSE;out[n++]=*p++;}
    out[n]=0;return *p=='\"';
}
static BOOL flag(const char *json,const char *key,BOOL fallback) {
    const char *p=field(json,key);return p?!strncmp(p,"true",4):fallback;
}
static unsigned long long number(const char *json,const char *key,unsigned long long fallback) {
    const char *p=field(json,key);return p && *p>='0' && *p<='9'?strtoull(p,NULL,10):fallback;
}
static DWORD virtual_key(const char *key) {
    size_t len=strlen(key);
    if(len==1 && ((*key>='A' && *key<='Z')||(*key>='0' && *key<='9')))return (DWORD)*key;
    if(*key=='F' && len>1 && len<=3) {char *end;long n=strtol(key+1,&end,10);if(!*end && n>=1 && n<=12)return VK_F1+(DWORD)n-1;}
    return 0;
}
static HWND input_target(void) {
    HWND root=GetForegroundWindow();DWORD tid=GetWindowThreadProcessId(root,NULL);
    GUITHREADINFO info={sizeof info};
    return tid && GetGUIThreadInfo(tid,&info) && info.hwndFocus?info.hwndFocus:root;
}
static BOOL emit_command(const char *event,int tone) {
    char value[200];
    if(tone>=0)snprintf(value,sizeof value,"{\"event\":\"tone\",\"tone\":%d,\"hwnd\":%llu}\n",tone,(unsigned long long)(ULONG_PTR)input_target());
    else snprintf(value,sizeof value,"{\"event\":\"%s\",\"hwnd\":%llu}\n",event,(unsigned long long)(ULONG_PTR)input_target());
    return transmit(value);
}
static void stop_caps(void) {
    ks_stop(0);for(int i=0;i<4;i++) {UnregisterHotKey(NULL,100+i);cap_event[i]=NULL;}
}
static DWORD configure(const char *json) {
    stop_caps();DWORD vk[4]={0},count=0,cycle=0,modifiers[4]={0},all_keys[4]={0};BOOL present[4]={0};
    const char *enabled[]={"selector","ime","chinese","traditional"};
    const char *mode_keys[]={"mode","ime_mode","chinese_mode","traditional_mode"};
    const char *key_keys[]={"key","ime_key","chinese_key","traditional_key"};
    const char *defaults[]={"Q","A","C","T"};
    BOOL tones=flag(json,"tones",FALSE);
    for(int i=0;i<4;i++) {
        if(!flag(json,enabled[i],i==0))continue;
        char mode[40],key[20];
        if(!text(json,mode_keys[i],mode,sizeof mode,"caps")||!text(json,key_keys[i],key,sizeof key,defaults[i]))return ERROR_INVALID_DATA;
        DWORD value=virtual_key(key);if(!value)return ERROR_INVALID_DATA;
        DWORD mod=0;
        if(strcmp(mode,"caps")) {
            if(!strcmp(mode,"ctrl_shift"))mod=MOD_CONTROL|MOD_SHIFT;
            else if(!strcmp(mode,"ctrl_alt"))mod=MOD_CONTROL|MOD_ALT;
            else return ERROR_INVALID_DATA;
        }
        if(tones && !mod && value>='0' && value<='4')return ERROR_HOTKEY_ALREADY_REGISTERED;
        for(int n=0;n<i;n++)if(present[n] && modifiers[n]==mod && all_keys[n]==value)return ERROR_HOTKEY_ALREADY_REGISTERED;
        present[i]=TRUE;modifiers[i]=mod;all_keys[i]=value;
        if(!mod) {cap_event[count]=names[i];vk[count++]=value;if(i==3)cycle=value;}
    }
    for(int i=0;i<4;i++)if(present[i] && modifiers[i]) {
        if(!RegisterHotKey(NULL,100+i,modifiers[i]|MOD_NOREPEAT,all_keys[i])) {DWORD error=GetLastError();stop_caps();return error;}
    }
    if(count || tones) {
        if(!ks_start(0,GetCurrentThreadId(),vk[0])) {DWORD error=GetLastError();stop_caps();return error;}
        ks_set_secondary(vk[1]);ks_set_tertiary(vk[2]);ks_set_quaternary(vk[3]);ks_set_cycle_key(cycle);ks_set_tones(tones);
    }
    return 0;
}
static BOOL command(const char *json) {
    char op[60],reply[220];DWORD error=0;
    if(!text(json,"operation",op,sizeof op,""))return FALSE;
    if(!strcmp(op,"caps-start"))error=configure(json);
    else if(!strcmp(op,"caps-stop"))stop_caps();
    else if(!strcmp(op,"navigation-start")) {
        if(!nav_running) {nav_running=ks_start(1,GetCurrentThreadId(),0);if(!nav_running)error=GetLastError();}
    } else if(!strcmp(op,"navigation-stop")) {ks_stop(1);nav_running=FALSE;}
    else if(!strcmp(op,"active")) {
        const char *active=field(json,"active");int mode=active && !strncmp(active,"true",4)?1:(int)number(json,"active",0);
        if(mode<0 || mode>3)error=ERROR_INVALID_DATA;
        else {ks_set_nav_target((HWND)(ULONG_PTR)number(json,"target",0));ks_set_active(mode);}
    } else error=ERROR_INVALID_FUNCTION;
    if(error)snprintf(reply,sizeof reply,"{\"id\":%llu,\"error\":\"Native keyboard command failed (%lu)\"}\n",number(json,"id",0),(unsigned long)error);
    else snprintf(reply,sizeof reply,"{\"id\":%llu,\"error\":null}\n",number(json,"id",0));
    return transmit(reply);
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR args,int show) {
    int argc=0;wchar_t **argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    if(!argv || argc!=2) {if(argv)LocalFree(argv);return 2;}
    wchar_t *end;unsigned long port=wcstoul(argv[1],&end,10);BOOL valid=port>0 && port<=65535 && !*end;
    char token[65]={0};
    DWORD received=0;
    while(valid && received<64){DWORD n=0;if(!ReadFile(GetStdHandle(STD_INPUT_HANDLE),token+received,64-received,&n,NULL)||!n){valid=FALSE;break;}received+=n;}
    for(int i=0;valid && i<64;i++) {char c=token[i];valid=(c>='0'&&c<='9')||(c>='a'&&c<='f');}
    LocalFree(argv);if(!valid)return 2;
    WSADATA data;if(WSAStartup(MAKEWORD(2,2),&data))return 3;
    channel=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(channel==INVALID_SOCKET) {WSACleanup();return 3;}
    struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_port=htons((u_short)port);address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if(connect(channel,(struct sockaddr*)&address,sizeof address)) {closesocket(channel);WSACleanup();return 4;}
    BOOL nodelay=TRUE;setsockopt(channel,IPPROTO_TCP,TCP_NODELAY,(char*)&nodelay,sizeof nodelay);
    DWORD timeout=1000;setsockopt(channel,SOL_SOCKET,SO_SNDTIMEO,(char*)&timeout,sizeof timeout);
    char hello[100];snprintf(hello,sizeof hello,"{\"token\":\"%s\"}\n",token);
    if(!transmit(hello)) {closesocket(channel);WSACleanup();return 4;}
    SecureZeroMemory(token,sizeof token);SecureZeroMemory(hello,sizeof hello);
    WSAEVENT ready=WSACreateEvent();WSAEventSelect(channel,ready,FD_READ|FD_CLOSE);
    char buffer[16385];size_t used=0;BOOL running=TRUE;MSG message;PeekMessageW(&message,NULL,0,0,PM_NOREMOVE);
    while(running) {
        DWORD signaled=MsgWaitForMultipleObjects(1,&ready,FALSE,INFINITE,QS_ALLINPUT);
        if(signaled==WAIT_OBJECT_0) {
            WSANETWORKEVENTS events={0};WSAEnumNetworkEvents(channel,ready,&events);
            for(;;) {
                int n=recv(channel,buffer+used,(int)(16384-used),0);
                if(n==0) {running=FALSE;break;}
                if(n<0) {if(WSAGetLastError()!=WSAEWOULDBLOCK)running=FALSE;break;}
                used+=n;buffer[used]=0;char *line;
                while((line=memchr(buffer,'\n',used))) {
                    size_t size=line-buffer;*line=0;
                    if(!command(buffer)) {running=FALSE;break;}
                    used-=size+1;memmove(buffer,line+1,used);buffer[used]=0;
                }
                if(!running || used>=16384) {running=FALSE;break;}
            }
            if(events.lNetworkEvents&FD_CLOSE)running=FALSE;
        } else if(signaled==WAIT_FAILED)break;
        while(running && PeekMessageW(&message,NULL,0,0,PM_REMOVE)) {
            if(message.message==WM_QUIT) {running=FALSE;break;}
            if(message.message==WM_HOTKEY && message.wParam>=100 && message.wParam<104)running=emit_command(names[message.wParam-100],-1);
            else if(message.message==KS_COMMAND) {
                if(message.wParam>=13) {char json[100];snprintf(json,sizeof json,"{\"event\":\"navigation\",\"key\":%llu}\n",(unsigned long long)message.wParam);running=transmit(json);}
                else if(message.wParam>=4 && message.wParam<=8)running=emit_command("tone",(int)message.wParam-4);
                else if(message.wParam<4 && cap_event[message.wParam])running=emit_command(cap_event[message.wParam],-1);
            } else {TranslateMessage(&message);DispatchMessageW(&message);}
        }
    }
    stop_caps();ks_stop(1);closesocket(channel);WSACloseEvent(ready);WSACleanup();return 0;
}
