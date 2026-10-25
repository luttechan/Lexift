/* Pure parser/state tests. No hooks, SendInput or external windows. */
#define wWinMain original_worker_entry
#include "../keyboard_worker.c"
#undef wWinMain

int main(void) {
    unsigned failed=0,passed=0;
    for(unsigned mode=0;mode<4;mode++) {
        char json[180];snprintf(json,sizeof json,"{\"id\":7,\"operation\":\"active\",\"active\":%u,\"target\":1099511627777}",mode);
        DWORD actual=(DWORD)number(json,"active",99);
        if(actual==mode && number(json,"target",0)==1099511627777ULL)passed++;else failed++;
    }
    const char *boolean="{\"operation\":\"active\",\"active\":true}";
    if(flag(boolean,"active",FALSE))passed++;else failed++;
    const char *value_first="{\"key\":\"active\",\"active\":2}";
    if(number(value_first,"active",99)==2)passed++;else failed++;
    const char *escaped="{\"operation\":\"active\",\"note\":\"\\\"active\\\":0\",\"active\":3}";
    if(number(escaped,"active",99)==3)passed++;else failed++;
    const char *spaced="{ \"operation\" : \"active\", \"active\"\t: \n1 }";
    if(number(spaced,"active",99)==1)passed++;else failed++;
    const char *existing="{\"operation\":\"caps-start\",\"mode\":\"caps\",\"key\":\"Q\",\"ime\":true}";
    char key[20];
    if(text(existing,"key",key,sizeof key,"") && !strcmp(key,"Q") && flag(existing,"ime",FALSE))passed++;else failed++;
    /* Exercise the real command path and its acknowledgements over owned
     * loopback sockets. No navigation hook or input events are installed. */
    WSADATA data;WSAStartup(MAKEWORD(2,2),&data);
    SOCKET listener=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    int length=sizeof address;bind(listener,(struct sockaddr*)&address,sizeof address);listen(listener,1);getsockname(listener,(struct sockaddr*)&address,&length);
    channel=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);connect(channel,(struct sockaddr*)&address,sizeof address);
    SOCKET peer=accept(listener,NULL,NULL);DWORD timeout=1000;setsockopt(peer,SOL_SOCKET,SO_RCVTIMEO,(char*)&timeout,sizeof timeout);
    const unsigned requested[]={0,1,2,3,2,0},expected[]={0,1,2,3,3,0};
    for(unsigned i=0;i<6;i++) {
        char json[128],reply[256];snprintf(json,sizeof json,"{\"id\":%u,\"operation\":\"active\",\"active\":%u}",i+1,requested[i]);
        BOOL sent=command(json);int got=recv(peer,reply,sizeof reply-1,0);if(got>0)reply[got]=0;
        if(sent && got>0 && strstr(reply,"\"error\":null") && (unsigned)InterlockedCompareExchange(&hooks[1].active,0,0)==expected[i])passed++;else failed++;
    }
    closesocket(peer);closesocket(channel);closesocket(listener);channel=INVALID_SOCKET;WSACleanup();
    printf("{\"passed\":%u,\"failed\":%u}\n",passed,failed);
    return failed?1:0;
}
