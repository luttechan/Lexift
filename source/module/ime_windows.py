from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from layout_profiles import ime_capabilities, SIMPLIFIED_CHINESE, TRADITIONAL_CHINESE

LANG_JA = 0x0411
LANG_KO = 0x0412
WM_INPUTLANGCHANGEREQUEST = 0x0050
WM_IME_CONTROL = 0x0283
IMC_GETCONVERSIONMODE = 0x0001
IMC_SETCONVERSIONMODE = 0x0002
IMC_GETOPENSTATUS = 0x0005
IMC_SETOPENSTATUS = 0x0006
IME_CMODE_NATIVE = 0x0001
IME_CMODE_KATAKANA = 0x0002
IME_CMODE_FULLSHAPE = 0x0008
IME_CMODE_ROMAN = 0x0010
SMTO_ABORTIFHUNG = 0x0002
IME_TIMEOUT_MS = 60
GA_ROOT = 2
VK_CAPITAL = 0x14
VK_HANGUL = 0x15
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_NONCONVERT = 0x1D
VK_LWIN = 0x5B
VK_SPACE = 0x20
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001
INPUT_KEYBOARD = 1


class IMEError(Exception):
    pass


if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    imm32 = ctypes.WinDLL("imm32", use_last_error=True)
    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("_pad", ctypes.c_void_p * 4)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    user32.GetKeyboardLayoutList.restype = ctypes.c_int
    user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
    user32.GetKeyboardLayout.restype = ctypes.c_void_p
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                            wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                                            ctypes.POINTER(ctypes.c_size_t)]
    user32.SendMessageTimeoutW.restype = ctypes.c_void_p
    imm32.ImmGetDefaultIMEWnd.argtypes = [wintypes.HWND]
    imm32.ImmGetDefaultIMEWnd.restype = wintypes.HWND
    imm32.ImmSimulateHotKey.argtypes = [wintypes.HWND, wintypes.DWORD]
    imm32.ImmSimulateHotKey.restype = wintypes.BOOL

    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
            ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
            ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
            ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
            ("rcCaret", wintypes.RECT),
        ]
    user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
    user32.GetGUIThreadInfo.restype = wintypes.BOOL


def get_target_window() -> int:
    if sys.platform != "win32":
        return 0
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(info)
    if tid and user32.GetGUIThreadInfo(tid, ctypes.byref(info)) and info.hwndFocus:
        return int(info.hwndFocus)
    return int(hwnd)


def _root(hwnd: int) -> int:
    return int(user32.GetAncestor(hwnd, GA_ROOT) or hwnd)


def foreground_target(hwnd: int) -> bool:
    """Restore focus from our selector only; never take it from another app."""
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return False
    root = _root(hwnd)
    foreground = int(user32.GetForegroundWindow() or 0)
    if foreground != root:
        owner = wintypes.DWORD()
        if not foreground or not user32.GetWindowThreadProcessId(foreground, ctypes.byref(owner)):
            return False
        if owner.value != os.getpid():
            return False
        user32.SetForegroundWindow(root)
    return target_is_foreground(hwnd)


def target_is_foreground(hwnd: int) -> bool:
    """Check focus without activating anything, including another editor child."""
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return False
    return (int(user32.GetForegroundWindow() or 0) == _root(hwnd)
            and get_target_window() == hwnd)


def _installed_hkl(language: int) -> int:
    count = user32.GetKeyboardLayoutList(0, None)
    if count <= 0:
        raise IMEError("Windows에서 키보드 입력기 목록을 읽지 못했습니다.")
    array = (ctypes.c_void_p * count)()
    size = user32.GetKeyboardLayoutList(count, array)
    for hkl in array[:size]:
        if hkl and (hkl & 0xFFFF) == language:
            return int(hkl)
    display = {LANG_KO: "한국어 Microsoft IME", LANG_JA: "일본어 Microsoft IME"}
    raise IMEError(f"{display.get(language, '해당 입력기')}가 설치되어 있지 않습니다. Windows 언어 설정에서 추가하세요.")


def request_hkl(hwnd: int, hkl: int, to_root: bool = False) -> None:
    """Request a specific installed Windows input locale, preserving layout variants."""
    if sys.platform != "win32":
        raise IMEError("Windows에서만 사용할 수 있습니다.")
    if not hwnd or not user32.IsWindow(hwnd):
        raise IMEError("입력 중이던 창이 닫혔거나 찾을 수 없습니다.")
    count = user32.GetKeyboardLayoutList(0, None)
    items = (ctypes.c_void_p * max(count, 1))()
    found = user32.GetKeyboardLayoutList(count, items) if count else 0
    mask = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
    if (hkl & mask) not in {(int(item) & mask) for item in items[:found] if item}:
        raise IMEError("지정한 입력기가 Windows 목록에 없습니다. 설정에서 입력기를 새로 검색하세요.")
    receiver = _root(hwnd) if to_root else hwnd
    if not user32.PostMessageW(receiver, WM_INPUTLANGCHANGEREQUEST, 0, hkl):
        raise IMEError("입력기 변경이 거부됐습니다. 대상 프로그램의 실행 권한을 확인하세요.")


def current_hkl(hwnd: int) -> int:
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return 0
    thread_id = user32.GetWindowThreadProcessId(hwnd, None)
    return int(user32.GetKeyboardLayout(thread_id) or 0)


def request_language(hwnd: int, language: int, to_root: bool = False) -> None:
    if sys.platform != "win32":
        raise IMEError("Windows에서만 사용할 수 있습니다.")
    if not hwnd or not user32.IsWindow(hwnd):
        raise IMEError("원래 입력하던 창이 닫혔거나 찾을 수 없습니다.")
    hkl = _installed_hkl(language)
    receiver = _root(hwnd) if to_root else hwnd
    if not user32.PostMessageW(receiver, WM_INPUTLANGCHANGEREQUEST, 0, hkl):
        raise IMEError("Windows가 입력기 변경 메시지를 거부했습니다. 관리자 권한 프로그램인지 확인하세요.")


def current_language(hwnd: int) -> int:
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return 0
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    return int(user32.GetKeyboardLayout(tid) or 0) & 0xFFFF


def _ime_cmd(hwnd: int, command: int, value: int = 0, *, timeout_ms: int = IME_TIMEOUT_MS) -> tuple[bool, int]:
    ime = imm32.ImmGetDefaultIMEWnd(hwnd)
    if not ime:
        return False, 0
    result = ctypes.c_size_t(0)
    sent = user32.SendMessageTimeoutW(ime, WM_IME_CONTROL, command, value,
                                      SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result))
    return bool(sent), int(result.value)


def _mode(hwnd: int, *, timeout_ms: int = IME_TIMEOUT_MS) -> tuple[int | None, bool | None]:
    ok, conversion = _ime_cmd(hwnd, IMC_GETCONVERSIONMODE, timeout_ms=timeout_ms)
    opened, open_value = _ime_cmd(hwnd, IMC_GETOPENSTATUS, timeout_ms=timeout_ms)
    return (conversion if ok else None, bool(open_value) if opened else None)


def _native_state(conversion, opened, native_conversion):
    if opened is False:
        return False
    if native_conversion:
        if conversion is None:
            return None
        if not conversion & IME_CMODE_NATIVE:
            return False
        return True if opened is True else None
    return opened


def _generic_mode(hwnd, native_conversion):
    if native_conversion:
        return _mode(hwnd, timeout_ms=IME_TIMEOUT_MS)
    ok, opened = _ime_cmd(hwnd, IMC_GETOPENSTATUS, timeout_ms=IME_TIMEOUT_MS)
    return None, bool(opened) if ok else None


def ime_native_status(hwnd: int) -> bool | None:
    supported, native_conversion = ime_capabilities(current_hkl(hwnd))
    if not supported:
        return None
    conversion, opened = _generic_mode(hwnd, native_conversion)
    return _native_state(conversion, opened, native_conversion)


def ime_set_native(hwnd: int, native: bool) -> bool:
    """Set an IME's native/Latin mode without selecting a different keyboard.

    Respect advertised capabilities and retain width, punctuation and other bits.
    Read back the state; a successfully delivered command is not confirmation.
    """
    if not target_is_foreground(hwnd):
        return False
    hkl = current_hkl(hwnd)
    supported, native_conversion = ime_capabilities(hkl)
    if not supported:
        return False
    conversion, opened = _generic_mode(hwnd, native_conversion)
    if _native_state(conversion, opened, native_conversion) is native:
        return True
    if native_conversion and conversion is None:
        return False
    actions = [(IMC_SETOPENSTATUS, int(native))]
    if native_conversion:
        flags = conversion | IME_CMODE_NATIVE if native else conversion & ~IME_CMODE_NATIVE
        actions.insert(1 if native else 0, (IMC_SETCONVERSIONMODE, flags))
    for command, value in actions:
        if not target_is_foreground(hwnd) or current_hkl(hwnd) != hkl:
            return False
        _ime_cmd(hwnd, command, value, timeout_ms=IME_TIMEOUT_MS)
    return ime_native_status(hwnd) is native


def ime_toggle_native(hwnd: int, native: bool) -> bool:
    """One guarded Windows IME toggle, only for documented language commands."""
    if not target_is_foreground(hwnd):
        return False
    hkl = current_hkl(hwnd)
    state = ime_native_status(hwnd)
    if state is None or state is native:
        return False
    langid = hkl & 0xFFFF
    identifier = (0x10 if langid in SIMPLIFIED_CHINESE else
                  0x70 if langid in TRADITIONAL_CHINESE else
                  0x30 if langid == LANG_JA else None)
    if identifier is None or not target_is_foreground(hwnd) or current_hkl(hwnd) != hkl:
        return False
    return bool(imm32.ImmSimulateHotKey(hwnd, identifier))


def _send_keys(*keys: int) -> bool:
    """Send key chord; all keys are released before returning."""
    if sys.platform != "win32":
        return False
    inputs = []
    for k in keys:
        inputs.append(INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(k, 0, 0, 0, 0))))
    for k in reversed(keys):
        inputs.append(INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(k, 0, KEYEVENTF_KEYUP, 0, 0))))
    array = (INPUT * len(inputs))(*inputs)
    return user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT)) == len(inputs)


def korean_is_hangul(hwnd: int, *, timeout_ms: int = IME_TIMEOUT_MS) -> bool | None:
    conversion, opened = _mode(hwnd,timeout_ms=timeout_ms)
    if opened is False:
        return False
    if conversion is not None:
        return bool(conversion & IME_CMODE_NATIVE)
    return opened


def korean_set(hwnd: int, hangul: bool) -> bool:
    """Set Korean IME native vs Latin input; does not activate a US layout."""
    if current_language(hwnd) != LANG_KO:
        return False
    hkl = current_hkl(hwnd)
    if korean_is_hangul(hwnd) == hangul:
        return True
    for command, value in ((IMC_SETOPENSTATUS, int(hangul)),
                           (IMC_SETCONVERSIONMODE, IME_CMODE_NATIVE if hangul else 0)):
        if not target_is_foreground(hwnd) or current_hkl(hwnd) != hkl:
            return False
        _ime_cmd(hwnd, command, value)
    return korean_is_hangul(hwnd) == hangul


def korean_toggle_key(hwnd: int) -> bool:
    """Hardware-scan Hangul toggle, for Korean IME in Chromium/WebView2 too.

    Physical Korean Han/Yeong commonly reports scan 0x72 (extended).
    SendInput virtual-key VK_HANGUL alone is ignored by some TSF editors.
    """
    if current_language(hwnd) != LANG_KO or not target_is_foreground(hwnd):
        return False
    scan = 0x72
    down = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(
        0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_EXTENDEDKEY, 0, 0)))
    up = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=KEYBDINPUT(
        0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0, 0)))
    events = (INPUT * 2)(down, up)
    return user32.SendInput(2, events, ctypes.sizeof(INPUT)) == 2


_JAPANESE_MODES = {
    "hiragana": IME_CMODE_NATIVE | IME_CMODE_FULLSHAPE | IME_CMODE_ROMAN,
    "katakana_full": IME_CMODE_NATIVE | IME_CMODE_KATAKANA | IME_CMODE_FULLSHAPE | IME_CMODE_ROMAN,
    "katakana_half": IME_CMODE_NATIVE | IME_CMODE_KATAKANA | IME_CMODE_ROMAN,
}


def japanese_matches(hwnd: int, kind: str) -> bool:
    if current_language(hwnd) != LANG_JA:
        return False
    conversion, opened = _mode(hwnd)
    if conversion is None or opened is False:
        return False
    mask = IME_CMODE_NATIVE | IME_CMODE_KATAKANA | IME_CMODE_FULLSHAPE
    return (conversion & mask) == (_JAPANESE_MODES[kind] & mask)


def japanese_set(hwnd: int, kind: str) -> bool:
    if kind not in _JAPANESE_MODES:
        raise IMEError("지원하지 않는 일본어 모드입니다.")
    if current_language(hwnd) != LANG_JA:
        return False
    hkl = current_hkl(hwnd)
    if japanese_matches(hwnd, kind):
        return True
    for command, value in ((IMC_SETOPENSTATUS, 1),
                           (IMC_SETCONVERSIONMODE, _JAPANESE_MODES[kind])):
        if not target_is_foreground(hwnd) or current_hkl(hwnd) != hkl:
            return False
        _ime_cmd(hwnd, command, value)
    return japanese_matches(hwnd, kind)


def japanese_fallback_key(hwnd: int, kind: str) -> bool:
    """Official MS IME hotkeys (not F7/F8, which alter composition only).

    Hiragana: Ctrl+CapsLock, Full Katakana: Alt+CapsLock.
    Half Katakana: NonConvert cycles; caller checks state after each cycle.
    """
    if current_language(hwnd) != LANG_JA or not target_is_foreground(hwnd):
        return False
    if kind == "hiragana":
        return _send_keys(VK_CONTROL, VK_CAPITAL)
    if kind == "katakana_full":
        return _send_keys(VK_MENU, VK_CAPITAL)
    if kind == "katakana_half":
        return _send_keys(VK_NONCONVERT)
    return False


def cycle_windows_language(hwnd: int) -> bool:
    """Fallback through the OS language-switch hotkey (Win+Space).

    This uses the Windows input-language switcher when a target does not
    honor WM_INPUTLANGCHANGEREQUEST, and is verified by the caller.
    """
    if not target_is_foreground(hwnd):
        return False
    return _send_keys(VK_LWIN, VK_SPACE)
