#include <assert.h>
#include <stdio.h>
#include "../module/native_hooks.c"

static void key(DWORD vk,BOOL down,DWORD time) {
    KBDLLHOOKSTRUCT event={0};
    event.vkCode=vk;
    event.time=time;
    caps_proc(HC_ACTION,down?WM_KEYDOWN:WM_KEYUP,(LPARAM)&event);
}

static void configure(BOOL selectorEnabled) {
    ZeroMemory(&hooks[0],sizeof(Hook));
    hooks[0].caps.trigger=selectorEnabled?'Q':'A';
    hooks[0].secondary=selectorEnabled?'A':0;
    hooks[0].ime_guard_key='A';
}

int main(void) {
    for(int selector=0;selector<2;selector++) {
        configure(selector);
        key(VK_CAPITAL,TRUE,100);
        key(VK_CAPITAL,FALSE,120);
        key('A',TRUE,121);
        assert(!hooks[0].caps.chord);

        configure(selector);
        key(VK_CAPITAL,TRUE,100);
        key('A',TRUE,118);
        assert(!hooks[0].caps.chord && hooks[0].caps.used);

        configure(selector);
        key(VK_CAPITAL,TRUE,100);
        key('A',TRUE,170);
        assert(hooks[0].caps.chord);

        configure(selector);
        key('A',TRUE,100);
        key(VK_CAPITAL,TRUE,180);
        key('A',TRUE,240);
        assert(!hooks[0].caps.chord && hooks[0].caps.used);
    }
    puts("Caps+A overlap: 8 checks passed");
    return 0;
}
