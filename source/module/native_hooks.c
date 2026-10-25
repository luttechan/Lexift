/* Lexift's low-level hooks must never acquire Python's GIL.
 * Only selector commands leave this native thread, using PostThreadMessage.
 * No allocation, socket I/O, IME queries or Python callbacks in either hook.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#define API __declspec(dllexport)
#define KS_COMMAND (WM_APP + 0x51)
#define KS_REPLAY (WM_APP + 0x52)
#define KS_REPLAY_KEY (WM_APP + 0x53)
#define SWALLOW 1
#define FIRE 2
#define REPLAY 4
#define FIRE_IME 8
#define FIRE_CHINESE 16
#define FIRE_TRADITIONAL 32

typedef struct { DWORD trigger, held, used, suppressed, chord; } CapsState;
typedef struct {
    HANDLE thread, ready;
    DWORD thread_id, receiver, trigger, error;
    int kind;
    volatile LONG active;
    PVOID volatile target;
    HHOOK hook;
    CapsState caps;
    volatile LONG secondary;
    DWORD secondary_suppressed;
    volatile LONG tertiary;
    DWORD tertiary_suppressed;
    volatile LONG quaternary;
    DWORD quaternary_suppressed;
    volatile LONG cycle_key;
    volatile LONG tones;
    BYTE tone_held[10];
    BYTE held[256];
    BYTE replayed[256];
} Hook;
static Hook hooks[2];

API DWORD ks_caps_step(CapsState *s, DWORD vk, BOOL down) {
    if (vk == VK_CAPITAL) {
        if (down) {
            if (!s->held) { s->held = 1; s->used = s->chord = 0; }
            return SWALLOW;
        }
        if (s->held) {
            DWORD result = SWALLOW | ((!s->used && !s->chord) ? REPLAY : 0);
            s->held = s->used = s->chord = 0;
            return result;
        }
        return 0;
    }
    if (vk == s->trigger && s->suppressed) {
        if (!down) s->suppressed = 0;
        return SWALLOW;
    }
    if (vk == s->trigger && down && s->held && s->chord) {
        s->suppressed = 1;
        return SWALLOW;
    }
    if (vk == s->trigger && down && s->held && !s->used) {
        s->suppressed = s->chord = 1;
        return SWALLOW | FIRE;
    }
    if (down && s->held && !s->used && !s->chord) {
        s->used = 1;
        return REPLAY;
    }
    return 0;
}

/* One Caps state owns both chords: two independent hooks would consume each
 * other's Caps events and replay unwanted toggles. Suppression survives Caps-up.
 */
API DWORD ks_caps_multi_step(CapsState *s, DWORD *suppressed, DWORD vk, BOOL down, DWORD secondary) {
    if (secondary && vk == secondary && secondary != s->trigger) {
        if (*suppressed) {
            if (!down) *suppressed = 0;
            return SWALLOW;
        }
        if (down && s->held && !s->used) {
            *suppressed = 1;
            if (!s->chord) { s->chord = 1; return SWALLOW | FIRE_IME; }
            return SWALLOW;
        }
    }
    return ks_caps_step(s, vk, down);
}

API DWORD ks_caps_three_step(CapsState *s, DWORD *second_held, DWORD *third_held,
                            DWORD vk, BOOL down, DWORD second, DWORD third) {
    if (third && third != s->trigger && third != second && vk == third) {
        if (*third_held) { if (!down) *third_held = 0; return SWALLOW; }
        if (down && s->held && !s->used) {
            *third_held = 1;
            if (!s->chord) { s->chord = 1; return SWALLOW | FIRE_CHINESE; }
            return SWALLOW;
        }
    }
    return ks_caps_multi_step(s, second_held, vk, down, second);
}

static BOOL selector_key(DWORD vk) {
    return (vk >= VK_LEFT && vk <= VK_DOWN) || vk == VK_RETURN ||
        vk == VK_ESCAPE || vk == VK_SPACE || (vk >= '0' && vk <= '9') ||
        (vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9) || (vk >= 'A' && vk <= 'E');
}

API DWORD ks_caps_four_step(CapsState *s,DWORD *second_held,DWORD *third_held,DWORD *fourth_held,
                           DWORD vk,BOOL down,DWORD second,DWORD third,DWORD fourth) {
    if(fourth && fourth!=s->trigger && fourth!=second && fourth!=third && vk==fourth) {
        if(*fourth_held) {if(!down)*fourth_held=0;return SWALLOW;}
        if(down && s->held && !s->used) {
            *fourth_held=1;
            if(!s->chord){s->chord=1;return SWALLOW|FIRE_TRADITIONAL;}
            return SWALLOW;
        }
    }
    return ks_caps_three_step(s,second_held,third_held,vk,down,second,third);
}

API DWORD ks_caps_cycle_step(CapsState *s,DWORD *second_held,DWORD *third_held,DWORD *fourth_held,
                            DWORD vk,BOOL down,DWORD second,DWORD third,DWORD fourth,DWORD cycle) {
    DWORD chord=s->chord;
    /* Fresh taps of the cycle key work with Caps held. Its own suppression
       still blocks auto-repeat; other shortcuts keep their existing behavior. */
    if(cycle && vk==cycle && down && s->held && !s->used)s->chord=0;
    DWORD action=ks_caps_four_step(s,second_held,third_held,fourth_held,vk,down,second,third,fourth);
    if(chord && vk!=VK_CAPITAL)s->chord=1;
    return action;
}

API BOOL ks_inline_key(DWORD vk) {
    return vk == VK_UP || vk == VK_DOWN || vk == VK_RETURN || vk == VK_SPACE || vk == VK_ESCAPE ||
        (vk >= '0' && vk <= '9') || (vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9);
}

API DWORD ks_navigation_step(BYTE *held, DWORD vk, BOOL down, BOOL active, BOOL modified) {
    if (vk > 255) return 0;
    if (held[vk]) {
        if (!down) held[vk] = 0;
        return SWALLOW;
    }
    if (!active || modified || !selector_key(vk)) return 0;
    if (down) { held[vk] = 1; return SWALLOW | FIRE; }
    return 0;
}

API DWORD ks_inline_keycode(DWORD vk,DWORD scan) {
    return vk == VK_PROCESSKEY && (scan & 0xff) == 0x39 ? VK_SPACE : vk;
}

API DWORD ks_navigation_event_step(BYTE *held,DWORD vk,DWORD scan,BOOL down,DWORD mode,BOOL foreground_matches,BOOL modified,BOOL injected) {
    vk=ks_inline_keycode(vk,scan);
    if(vk>255)return 0;
    BOOL active=mode!=0 && (mode<2 || foreground_matches);
    // IME-synthesized releases must clear our state, but must never fire commands.
    if(injected) { if(!down)held[vk]=0; return 0; }
    if(mode==3) {
        if(held[vk]) {if(!down)held[vk]=0;return SWALLOW;}
        if(active && !modified && (vk==VK_SPACE || vk==VK_RETURN)) {
            if(down){held[vk]=1;return SWALLOW;}
        }
        return 0;
    }
    // New text starts a new conversion. A missing Space-up from an earlier
    // composition must not suppress its confirmation. Preserve held-key repeats.
    if(down && ((vk>='A' && vk<='Z') || vk==VK_BACK || vk==VK_OEM_MINUS))held[VK_SPACE]=0;
    if(!held[vk] && (!active || !(mode==2?ks_inline_key(vk):selector_key(vk))))return 0;
    return ks_navigation_step(held,vk,down,active,modified);
}

API DWORD ks_caps_tone_step(CapsState *s,BYTE *held,DWORD vk,BOOL down,BOOL enabled) {
    if(vk<'0' || vk>'4')return 0;
    DWORD tone=vk-'0';
    if(held[tone]) {if(!down)held[tone]=0;return SWALLOW;}
    if(enabled && down && s->held && !s->used) {
        held[tone]=1;s->chord=1;
        return SWALLOW|((tone+1)<<8);
    }
    return 0;
}

/* Keep the two physical number banks independent, including their releases.
 * With Num Lock off Windows reports navigation VKs for the keypad; dedicated
 * navigation keys carry the extended flag and must keep their normal meaning.
 * The legacy five-byte state API above remains ABI compatible.
 */
API DWORD ks_caps_tone_event_step(CapsState *s,BYTE *held,DWORD vk,DWORD scan,BOOL extended,BOOL down,BOOL enabled,DWORD navigationMode) {
    BOOL keypad=vk>=VK_NUMPAD0 && vk<=VK_NUMPAD4;
    if(keypad)vk='0'+vk-VK_NUMPAD0;
    else if(!extended) {
        switch(scan&0xff) {
            case 0x52:if(vk==VK_INSERT){vk='0';keypad=TRUE;}break;
            case 0x4f:if(vk==VK_END){vk='1';keypad=TRUE;}break;
            case 0x50:if(vk==VK_DOWN){vk='2';keypad=TRUE;}break;
            case 0x51:if(vk==VK_NEXT){vk='3';keypad=TRUE;}break;
            case 0x4b:if(vk==VK_LEFT){vk='4';keypad=TRUE;}break;
        }
    }
    // Candidate/selector numbers take priority, even while Caps is still held
    // after opening that popup. Existing tone releases must still be drained.
    return ks_caps_tone_step(s,held+(keypad?5:0),vk,down,enabled && navigationMode==0);
}

static LRESULT CALLBACK caps_proc(int code, WPARAM message, LPARAM data) {
    Hook *h = &hooks[0];
    if (code == HC_ACTION && (message == WM_KEYDOWN || message == WM_KEYUP ||
                              message == WM_SYSKEYDOWN || message == WM_SYSKEYUP)) {
        KBDLLHOOKSTRUCT *key = (KBDLLHOOKSTRUCT *)data;
        if (!(key->flags & LLKHF_INJECTED)) {
            BOOL down = message == WM_KEYDOWN || message == WM_SYSKEYDOWN;
            DWORD vk = key->vkCode;
            /* Keep Caps+ordinary-key ordering without SendInput in the hook.
             * Queue matching key-ups too, so a fast release cannot overtake
             * the deferred key-down and leave a key logically pressed.
             */
            LPARAM flags = (key->scanCode & 0xffff) |
                ((key->flags & LLKHF_EXTENDED) ? 0x10000 : 0) |
                (!down ? 0x20000 : 0);
            if (vk < 256 && h->replayed[vk]) {
                if (!down) h->replayed[vk] = 0;
                if (PostThreadMessageW(h->thread_id, KS_REPLAY_KEY, vk, flags)) return 1;
            }
            DWORD toneAction=ks_caps_tone_event_step(&h->caps,h->tone_held,vk,key->scanCode,
                (key->flags & LLKHF_EXTENDED)!=0,down,InterlockedCompareExchange(&h->tones,0,0),
                (DWORD)InterlockedCompareExchange(&hooks[1].active,0,0));
            if(toneAction & 0xff00)PostThreadMessageW(h->receiver,KS_COMMAND,3+(toneAction>>8),0);
            if(toneAction & SWALLOW)return 1;
            DWORD action = ks_caps_cycle_step(&h->caps, &h->secondary_suppressed, &h->tertiary_suppressed,&h->quaternary_suppressed,
                key->vkCode, down, (DWORD)InterlockedCompareExchange(&h->secondary, 0, 0),
                (DWORD)InterlockedCompareExchange(&h->tertiary, 0, 0),
                (DWORD)InterlockedCompareExchange(&h->quaternary, 0, 0),
                (DWORD)InterlockedCompareExchange(&h->cycle_key, 0, 0));
            if (action & REPLAY) {
                if (vk != VK_CAPITAL && vk < 256) {
                    if (PostThreadMessageW(h->thread_id, KS_REPLAY, vk, flags)) {
                        h->replayed[vk] = 1;
                        return 1;
                    }
                } else PostThreadMessageW(h->thread_id, KS_REPLAY, 0, 0);
            }
            if (action & FIRE) PostThreadMessageW(h->receiver, KS_COMMAND, 0, 0);
            if (action & FIRE_IME) PostThreadMessageW(h->receiver, KS_COMMAND, 1, 0);
            if (action & FIRE_CHINESE) PostThreadMessageW(h->receiver, KS_COMMAND, 2, 0);
            if (action & FIRE_TRADITIONAL) PostThreadMessageW(h->receiver, KS_COMMAND, 3, 0);
            if (action & SWALLOW) return 1;
        }
    }
    return CallNextHookEx(h->hook, code, message, data);
}

static LRESULT CALLBACK navigation_proc(int code, WPARAM message, LPARAM data) {
    Hook *h = &hooks[1];
    if (code == HC_ACTION && (message == WM_KEYDOWN || message == WM_KEYUP ||
                              message == WM_SYSKEYDOWN || message == WM_SYSKEYUP)) {
        KBDLLHOOKSTRUCT *key = (KBDLLHOOKSTRUCT *)data;
        DWORD vk = ks_inline_keycode(key->vkCode,key->scanCode);
        if (vk < 256) {
            LONG mode = InterlockedCompareExchange(&h->active, 0, 0);
            BOOL active = mode != 0;
            if (mode >= 2 && GetForegroundWindow() != (HWND)InterlockedCompareExchangePointer(&h->target, NULL, NULL)) active = FALSE;
            {
                BOOL modified = active && ((GetAsyncKeyState(VK_CONTROL) |
                    GetAsyncKeyState(VK_MENU) | GetAsyncKeyState(VK_LWIN) |
                    GetAsyncKeyState(VK_RWIN)) & 0x8000);
                if(mode == 2 && ((vk >= '0' && vk <= '9') || (vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9)) &&
                   (GetAsyncKeyState(VK_SHIFT) & 0x8000)) modified=TRUE;
                BOOL down=message == WM_KEYDOWN || message == WM_SYSKEYDOWN;
                DWORD action = ks_navigation_event_step(h->held,key->vkCode,key->scanCode,down,mode,active,modified,
                    (key->flags & LLKHF_INJECTED)!=0);
                if (action & FIRE) {
                    if(mode==2 && (vk==VK_SPACE || vk==VK_RETURN))InterlockedExchange(&h->active,3);
                    PostThreadMessageW(h->receiver, KS_COMMAND, vk, 0);
                }
                if (action & SWALLOW) return 1;
            }
        }
    }
    return CallNextHookEx(h->hook, code, message, data);
}

static DWORD WINAPI hook_loop(void *parameter) {
    Hook *h = (Hook *)parameter;
    MSG message;
    HMODULE module = NULL;
    HOOKPROC proc = h->kind == 0 ? caps_proc : navigation_proc;
    PeekMessageW(&message, NULL, 0, 0, PM_NOREMOVE);
    h->thread_id = GetCurrentThreadId();
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
        GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)proc, &module);
    h->hook = SetWindowsHookExW(WH_KEYBOARD_LL, proc, module, 0);
    if (!h->hook) h->error = GetLastError();
    SetEvent(h->ready);
    if (!h->hook) return 0;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        if (message.message == KS_REPLAY || message.message == KS_REPLAY_KEY) {
            /* SendInput only after the low-level hook has returned. */
            INPUT events[3] = {0};
            UINT count = 0;
            if (message.message == KS_REPLAY) {
                events[0].type = events[1].type = INPUT_KEYBOARD;
                events[0].ki.wVk = events[1].ki.wVk = VK_CAPITAL;
                events[1].ki.dwFlags = KEYEVENTF_KEYUP;
                count = 2;
            }
            if (message.wParam) {
                INPUT *event = &events[count++];
                event->type = INPUT_KEYBOARD;
                event->ki.wVk = (WORD)message.wParam;
                event->ki.wScan = (WORD)(message.lParam & 0xffff);
                event->ki.dwFlags = ((message.lParam & 0x10000) ? KEYEVENTF_EXTENDEDKEY : 0) |
                    ((message.lParam & 0x20000) ? KEYEVENTF_KEYUP : 0);
            }
            SendInput(count, events, sizeof(INPUT));
        } else {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }
    UnhookWindowsHookEx(h->hook);
    h->hook = NULL;
    return 0;
}

API BOOL ks_start(int kind, DWORD receiver, DWORD trigger) {
    if (kind < 0 || kind > 1) { SetLastError(ERROR_INVALID_PARAMETER); return FALSE; }
    Hook *h = &hooks[kind];
    if (h->thread) { SetLastError(ERROR_ALREADY_EXISTS); return FALSE; }
    ZeroMemory(h, sizeof(*h));
    h->kind = kind; h->receiver = receiver; h->trigger = trigger; h->caps.trigger = trigger;
    h->ready = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!h->ready) return FALSE;
    h->thread = CreateThread(NULL, 0, hook_loop, h, 0, NULL);
    if (!h->thread) { CloseHandle(h->ready); h->ready = NULL; return FALSE; }
    DWORD wait = WaitForSingleObject(h->ready, 3000);
    if (wait != WAIT_OBJECT_0 || h->error) {
        DWORD error = h->error ? h->error : ERROR_TIMEOUT;
        PostThreadMessageW(h->thread_id, WM_QUIT, 0, 0);
        if (WaitForSingleObject(h->thread, 2000) == WAIT_OBJECT_0) {
            CloseHandle(h->thread); h->thread = NULL;
            CloseHandle(h->ready); h->ready = NULL;
        }
        SetLastError(error);
        return FALSE;
    }
    CloseHandle(h->ready); h->ready = NULL;
    return TRUE;
}

API void ks_set_active(BOOL active) {
    LONG mode=active>=0 && active<=3?active:active!=0;
    // Stale visibility updates must not unlock a commit already dispatched.
    if(mode==2)InterlockedCompareExchange(&hooks[1].active,2,0);
    if(mode!=2 || InterlockedCompareExchange(&hooks[1].active,0,0)!=3)InterlockedExchange(&hooks[1].active,mode);
}
API void ks_set_quaternary(DWORD key) { InterlockedExchange(&hooks[0].quaternary, key); }
API void ks_set_cycle_key(DWORD key) { InterlockedExchange(&hooks[0].cycle_key, key); }
API void ks_set_secondary(DWORD key) { InterlockedExchange(&hooks[0].secondary, key); }
API void ks_set_tertiary(DWORD key) { InterlockedExchange(&hooks[0].tertiary, key); }
API void ks_set_nav_target(HWND target) { InterlockedExchangePointer(&hooks[1].target, target); }

API BOOL ks_stop(int kind) {
    if (kind < 0 || kind > 1) return FALSE;
    Hook *h = &hooks[kind];
    if (!h->thread) return TRUE;
    InterlockedExchange(&h->active, 0);
    PostThreadMessageW(h->thread_id, WM_QUIT, 0, 0);
    if (WaitForSingleObject(h->thread, 2000) != WAIT_OBJECT_0) return FALSE;
    CloseHandle(h->thread); h->thread = NULL;
    if (h->ready) { CloseHandle(h->ready); h->ready = NULL; }
    return TRUE;
}

API void ks_set_tones(BOOL enabled) {InterlockedExchange(&hooks[0].tones,enabled);}
API DWORD ks_abi_version(void) { return 6; }
