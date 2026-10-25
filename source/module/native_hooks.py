"""Native hook callbacks pass ordinary input without entering Python."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import threading

COMMAND_MESSAGE = 0x8000 + 0x51
_library = None
_lock = threading.Lock()

def library():
    global _library
    with _lock:
        if _library is None:
            dll = ctypes.WinDLL(str(Path(__file__).with_name('kanashift_hooks.dll')), use_last_error=True)
            dll.ks_abi_version.restype = wintypes.DWORD
            if dll.ks_abi_version() != 6:
                raise RuntimeError('Incompatible Lexift keyboard module')
            dll.ks_start.argtypes = [ctypes.c_int, wintypes.DWORD, wintypes.DWORD]
            dll.ks_start.restype = wintypes.BOOL
            dll.ks_set_active.argtypes = [wintypes.BOOL]
            dll.ks_set_active.restype = None
            dll.ks_set_secondary.argtypes = [wintypes.DWORD]
            dll.ks_set_secondary.restype = None
            dll.ks_set_tertiary.argtypes = [wintypes.DWORD]
            dll.ks_set_tertiary.restype = None
            dll.ks_set_quaternary.argtypes = [wintypes.DWORD]
            dll.ks_set_quaternary.restype = None
            dll.ks_set_tones.argtypes=[wintypes.BOOL]
            dll.ks_set_tones.restype=None
            dll.ks_set_cycle_key.argtypes = [wintypes.DWORD]
            dll.ks_set_cycle_key.restype = None
            dll.ks_set_nav_target.argtypes = [wintypes.HWND]
            dll.ks_set_nav_target.restype = None
            dll.ks_stop.argtypes = [ctypes.c_int]
            dll.ks_stop.restype = wintypes.BOOL
            _library = dll
        return _library

def start(kind, thread_id, trigger=0):
    # PostThreadMessage requires the receiving Python thread to have a queue.
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                  wintypes.UINT, wintypes.UINT, wintypes.UINT]
    user32.PeekMessageW.restype = wintypes.BOOL
    message = wintypes.MSG()
    user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
    dll = library()
    if not dll.ks_start(kind, thread_id, trigger):
        raise ctypes.WinError(ctypes.get_last_error())
    return dll
