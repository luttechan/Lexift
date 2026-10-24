from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable
from i18n import tr

VK_CAPITAL = 0x14
VK_Q = 0x51
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WH_KEYBOARD_LL = 13
LLKHF_INJECTED = 0x10
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 1

MODES = ("caps", "ctrl_shift", "ctrl_alt")
MODE_LABELS = {"caps": "CapsLock", "ctrl_shift": "Ctrl + Shift", "ctrl_alt": "Ctrl + Alt"}
KEY_LABELS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") + tuple(f"F{i}" for i in range(1, 13))


def key_vk(key: str) -> int:
    key = key.upper().strip()
    if len(key) == 1 and key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        return ord(key)
    if key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
        return 0x70 + int(key[1:]) - 1
    raise ValueError(f"지원하지 않는 단축키: {key}")


@dataclass(frozen=True)
class HotkeyBinding:
    mode: str = "caps"
    key: str = "Q"

    def __post_init__(self):
        object.__setattr__(self, 'key', self.key.upper().strip())
        if self.mode not in MODES:
            raise ValueError(f"지원하지 않는 조합: {self.mode}")
        key_vk(self.key)

    @property
    def title(self) -> str:
        return f"{tr(MODE_LABELS[self.mode])} + {self.key.upper()}"

    @property
    def modifiers(self) -> int:
        return {
            "ctrl_shift": MOD_CONTROL | MOD_SHIFT,
            "ctrl_alt": MOD_CONTROL | MOD_ALT,
        }.get(self.mode, 0)


class CapsQState:
    """State machine for CapsLock + configurable key; testable without Windows.

    Returns (suppress_event, trigger_hud, replay_caps_tap).
    """
    def __init__(self, trigger_vk: int = VK_Q):
        self.trigger_vk = trigger_vk
        self.caps_held = False
        self.caps_used = False
        self.key_suppressed = False
        self.chord_used = False
        self._suppress_caps_release = False

    def handle(self, vk: int, down: bool) -> tuple[bool, bool, bool]:
        if vk == VK_CAPITAL:
            if down:
                if not self.caps_held:
                    self.caps_held = True
                    self.caps_used = False
                    self.chord_used = False
                return True, False, False
            if self.caps_held:
                tap = not self.caps_used and not self.chord_used
                self.caps_held = False
                self.caps_used = False
                self.chord_used = False
                return True, False, tap
            return False, False, False
        if vk == self.trigger_vk and self.key_suppressed:
            if not down:
                self.key_suppressed = False
            return True, False, False
        if vk == self.trigger_vk and down and self.caps_held and self.chord_used:
            # Suppress repeated presses while Caps is held; fire only once.
            self.key_suppressed = True
            return True, False, False
        if vk == self.trigger_vk and down and self.caps_held and not self.caps_used:
            self.key_suppressed = True
            self.chord_used = True
            return True, True, False
        if down and self.caps_held and not self.caps_used and not self.chord_used:
            self.caps_used = True
            return False, False, True
        return False, False, False


if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    LRESULT = ctypes.c_ssize_t
    ULONG_PTR = ctypes.c_size_t

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("_align", ctypes.c_void_p * 4)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

    LOW_LEVEL_PROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LOW_LEVEL_PROC, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.UnregisterHotKey.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostThreadMessageW.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE


def _send_caps_tap() -> None:
    if sys.platform != "win32":
        return
    events = (INPUT * 2)(
        INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(VK_CAPITAL, 0, 0, 0, 0))),
        INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(VK_CAPITAL, 0, KEYEVENTF_KEYUP, 0, 0))),
    )
    user32.SendInput(2, events, ctypes.sizeof(INPUT))


class CapsQHook:
    """Compatibility name: supports any HotkeyBinding, not just Caps+Q."""
    def __init__(self, on_hotkey: Callable[[int], None], binding: HotkeyBinding | None = None, on_ime=None, secondary_key='A', on_chinese=None, tertiary_key='C'):
        self.on_hotkey = on_hotkey
        self.on_ime = on_ime
        self.secondary_key = secondary_key
        self.on_chinese = on_chinese
        self.tertiary_key = tertiary_key
        self.binding = binding or HotkeyBinding()
        self.state = CapsQState(key_vk(self.binding.key))
        self.thread: threading.Thread | None = None
        self.thread_id = 0
        self._hook = None
        self._callback = None
        self._ready = threading.Event()
        self.error: str | None = None

    def start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Windows에서만 사용할 수 있습니다.")
        self._ready.clear()
        self.error = None
        self.thread = threading.Thread(target=self._loop, daemon=True, name="Lexift-Hotkey")
        self.thread.start()
        if not self._ready.wait(4):
            raise RuntimeError("단축키 등록 시간이 초과되었습니다.")
        if self.error:
            raise RuntimeError(self.error)

    def _loop(self) -> None:
        self.thread_id = kernel32.GetCurrentThreadId()
        if self.binding.mode != "caps":
            self._loop_native()
            return
        self._loop_caps()

    def _fire(self):
        try:
            self.on_hotkey(0)
        except Exception:
            # A keyboard-hook callback may not propagate exceptions through Win32.
            pass

    def _loop_native(self):
        mods = self.binding.modifiers | MOD_NOREPEAT
        if not user32.RegisterHotKey(None, HOTKEY_ID, mods, key_vk(self.binding.key)):
            self.error = (f"{self.binding.title} 단축키를 등록할 수 없습니다. "
                          f"다른 프로그램의 단축키와 겹치는지 확인하세요. (Win32 {ctypes.get_last_error()})")
            self._ready.set()
            return
        self._ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._fire()
                else:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)

    def _loop_caps(self):
        from native_hooks import start, COMMAND_MESSAGE
        try:
            native = start(0, self.thread_id, key_vk(self.binding.key))
            native.ks_set_secondary(key_vk(self.secondary_key) if self.on_ime else 0)
            native.ks_set_tertiary(key_vk(self.tertiary_key) if self.on_chinese else 0)
        except (OSError, RuntimeError) as error:
            self.error = f"키보드 후크 등록 실패 ({error})"
            self._ready.set()
            return
        self._ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == COMMAND_MESSAGE:
                    if msg.wParam == 2 and self.on_chinese:
                        self.on_chinese(0)
                    elif msg.wParam == 1 and self.on_ime:
                        self.on_ime(0)
                    else:
                        self._fire()
                else:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            native.ks_stop(0)

    def stop(self) -> None:
        if self.thread_id and self.thread and self.thread.is_alive():
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            if threading.current_thread() is not self.thread:
                self.thread.join(timeout=2)
        self.thread_id = 0


class HotkeyGroup:
    """Own exactly one Caps hook and independent RegisterHotKey threads.

    Roll back the entire group if any of the three registrations fails.
    """
    def __init__(self, entries):
        bindings=[binding for binding, callback in entries]
        if len(set(bindings)) != len(bindings):
            raise RuntimeError('단축키가 겹칩니다. 서로 다른 조합을 선택하세요.')
        caps=[entry for entry in entries if entry[0].mode=='caps']
        self.hooks=[CapsQHook(callback,binding) for binding,callback in entries if binding.mode!='caps']
        if caps:
            kwargs={}
            if len(caps)>1:
                kwargs.update(on_ime=caps[1][1],secondary_key=caps[1][0].key)
            if len(caps)>2:
                kwargs.update(on_chinese=caps[2][1],tertiary_key=caps[2][0].key)
            self.hooks.append(CapsQHook(caps[0][1],caps[0][0],**kwargs))

    def start(self):
        try:
            for hook in self.hooks:
                hook.start()
        except Exception:
            self.stop()
            raise

    def stop(self):
        for hook in reversed(self.hooks):
            hook.stop()


# Independent HUD navigation hook. It handles selector keys even when Windows
# declines to grant keyboard focus to the Qt tool window.
OVERLAY_KEYS = frozenset({0x25, 0x26, 0x27, 0x28, 0x0D, 0x1B, 0x20,
                          *range(0x30, 0x3A), *range(0x60, 0x6A), *range(0x41, 0x46)})


class OverlayKeyState:
    """Capture balanced keydown/up pairs only while the selector is visible."""
    def __init__(self):
        self.held: set[int] = set()

    def handle(self, vk: int, down: bool, active: bool, modified: bool = False) -> tuple[bool, bool]:
        # The corresponding key-up must be consumed even when the selector was
        # hidden by the earlier key-down (Enter, Escape or a number selection).
        if vk in self.held:
            if not down:
                self.held.discard(vk)
            return True, False
        if not active or modified or vk not in OVERLAY_KEYS:
            return False, False
        if down:
            self.held.add(vk)
            return True, True
        return False, False


class OverlayNavigationHook:
    """Windows low-level keyboard hook active only for HUD selector commands.

    The hook is installed once per running process to avoid a race between
    showing the overlay and installing a hook. All keys pass through normally
    while the HUD is closed. Qt GUI updates happen via a queued Qt Signal.
    """
    def __init__(self, on_key: Callable[[int], None]):
        self.on_key = on_key
        self.state = OverlayKeyState()
        self.active = threading.Event()
        self.mode = 0
        self.target = 0
        self.thread: threading.Thread | None = None
        self.thread_id = 0
        self._hook = None
        self._callback = None
        self._ready = threading.Event()
        self.error: str | None = None

    def set_active(self, active: bool, target=0) -> None:
        self.mode = int(active)
        self.target = int(target or 0)
        if active:
            self.active.set()
        else:
            self.active.clear()
        native = getattr(self, '_native', None)
        if native is not None:
            native.ks_set_nav_target(self.target)
            native.ks_set_active(self.mode)

    def start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Windows에서만 사용할 수 있습니다.")
        if self.thread is not None and self.thread.is_alive():
            return
        self.error = None
        self._ready.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="Lexift-Overlay-Keys")
        self.thread.start()
        if not self._ready.wait(4):
            raise RuntimeError("오버레이 키보드 연결 시간이 초과되었습니다.")
        if self.error:
            raise RuntimeError(self.error)

    def _loop(self) -> None:
        self.thread_id = kernel32.GetCurrentThreadId()
        from native_hooks import start, COMMAND_MESSAGE
        try:
            native = start(1, self.thread_id)
            self._native = native
            native.ks_set_nav_target(self.target)
            native.ks_set_active(self.mode)
        except (OSError, RuntimeError) as error:
            self.error = f"오버레이 키보드 후크 연결 실패 ({error})"
            self._ready.set()
            return
        self._ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == COMMAND_MESSAGE:
                    try:
                        self.on_key(int(msg.wParam))
                    except Exception:
                        pass
                else:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self.active.clear()
            native.ks_stop(1)
            self._native = None

    def stop(self) -> None:
        self.active.clear()
        if self.thread_id and self.thread and self.thread.is_alive():
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            if threading.current_thread() is not self.thread:
                self.thread.join(timeout=2)
        self.thread_id = 0
