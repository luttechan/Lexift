from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Sequence
from i18n import tr


class NativeDialogUnavailable(RuntimeError):
    """The native task-dialog control could not be opened."""


def _dialog_types():
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_int, wintypes.HWND, wintypes.UINT,
        wintypes.WPARAM, wintypes.LPARAM, ctypes.c_ssize_t,
    )

    class TaskDialogButton(ctypes.Structure):
        _fields_ = [("nButtonID", ctypes.c_int), ("pszButtonText", ctypes.c_wchar_p)]

    class TaskDialogConfig(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("hwndParent", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("dwFlags", wintypes.UINT),
            ("dwCommonButtons", wintypes.UINT),
            ("pszWindowTitle", ctypes.c_wchar_p),
            ("mainIcon", ctypes.c_void_p),
            ("pszMainInstruction", ctypes.c_wchar_p),
            ("pszContent", ctypes.c_wchar_p),
            ("cButtons", wintypes.UINT),
            ("pButtons", ctypes.POINTER(TaskDialogButton)),
            ("nDefaultButton", ctypes.c_int),
            ("cRadioButtons", wintypes.UINT),
            ("pRadioButtons", ctypes.POINTER(TaskDialogButton)),
            ("nDefaultRadioButton", ctypes.c_int),
            ("pszVerificationText", ctypes.c_wchar_p),
            ("pszExpandedInformation", ctypes.c_wchar_p),
            ("pszExpandedControlText", ctypes.c_wchar_p),
            ("pszCollapsedControlText", ctypes.c_wchar_p),
            ("footerIcon", ctypes.c_void_p),
            ("pszFooter", ctypes.c_wchar_p),
            ("pfCallback", callback_type),
            ("lpCallbackData", ctypes.c_ssize_t),
            ("cxWidth", wintypes.UINT),
        ]

    return TaskDialogButton, TaskDialogConfig, callback_type


def language_choices(languages: Sequence[tuple[str, str]]) -> tuple[tuple[int, str, str], ...]:
    """Stable radio IDs and native-language labels, independent of UI locale."""
    return tuple((100 + index, code, name) for index, (code, name) in enumerate(languages))


def choose_ui_language(languages: Sequence[tuple[str, str]], default: str = "ko") -> str | None:
    """Show a modal, foreground native Windows dialog for the first launch.

    Cancel returns None. An unavailable common-controls TaskDialog raises
    NativeDialogUnavailable so that the caller can use an always-on-top Qt
    fallback rather than silently select the wrong language.
    """
    if sys.platform != "win32":
        raise NativeDialogUnavailable("Windows TaskDialog is only available on Windows")
    choices = language_choices(languages)
    if not choices:
        raise ValueError("No interface languages are configured")

    TaskDialogButton, TaskDialogConfig, callback_type = _dialog_types()

    items = (TaskDialogButton * len(choices))(*[
        TaskDialogButton(choice_id, native_name)
        for choice_id, _, native_name in choices
    ])
    preferred = next((item_id for item_id, code, _ in choices if code == default), choices[0][0])
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    @callback_type
    def on_event(hwnd, notification, _wparam, _lparam, _data):
        # TDN_CREATED == 0. Force the first-run prompt above other windows.
        if notification == 0:
            # HWND_TOPMOST = -1, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
            user32.SetWindowPos(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0003 | 0x0040)
            user32.SetForegroundWindow(hwnd)
        return 0

    config = TaskDialogConfig()
    config.cbSize = ctypes.sizeof(TaskDialogConfig)
    config.dwFlags = 0x0008  # TDF_ALLOW_DIALOG_CANCELLATION
    config.dwCommonButtons = 0x0001 | 0x0008  # TDCBF_OK_BUTTON | TDCBF_CANCEL_BUTTON
    config.pszWindowTitle = "KanaShift"
    config.pszMainInstruction = "Choose your language / 표시 언어 선택"
    config.cRadioButtons = len(choices)
    config.pRadioButtons = items
    config.nDefaultRadioButton = preferred
    config.pfCallback = on_event
    config.cxWidth = 230  # dialog units

    selected_button = ctypes.c_int(0)
    selected_radio = ctypes.c_int(0)
    try:
        comctl = ctypes.WinDLL("comctl32", use_last_error=True)
        task_dialog = comctl.TaskDialogIndirect
        task_dialog.argtypes = [
            ctypes.POINTER(TaskDialogConfig), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(wintypes.BOOL),
        ]
        task_dialog.restype = ctypes.c_long
        status = task_dialog(ctypes.byref(config), ctypes.byref(selected_button),
                             ctypes.byref(selected_radio), None)
    except (AttributeError, OSError) as exc:
        raise NativeDialogUnavailable("Windows TaskDialogIndirect is unavailable") from exc

    if status != 0:
        raise NativeDialogUnavailable(f"Windows TaskDialog failed: HRESULT 0x{status & 0xffffffff:08X}")
    if selected_button.value != 1:  # IDOK == 1; closing or cancelling must not save a preference
        return None
    return next((code for item_id, code, _ in choices if item_id == selected_radio.value), default)


def confirm_quit(owner=None) -> bool:
    """Use explicit translated captions even when Windows has another UI language."""
    Button, Config, _callback = _dialog_types()
    buttons = (Button * 2)(Button(6, tr("종료")), Button(7, tr("취소")))
    config = Config()
    config.cbSize = ctypes.sizeof(config)
    config.hwndParent = owner
    config.dwFlags = 0x0008
    config.pszWindowTitle = "KanaShift"
    config.pszMainInstruction = tr("정말로 종료하시겠습니까?")
    config.cButtons = 2
    config.pButtons = buttons
    config.nDefaultButton = 7
    chosen = ctypes.c_int(0)
    try:
        api = ctypes.WinDLL("comctl32", use_last_error=True).TaskDialogIndirect
        api.argtypes = [ctypes.POINTER(Config), ctypes.POINTER(ctypes.c_int),
                        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(wintypes.BOOL)]
        api.restype = ctypes.c_long
        status = api(ctypes.byref(config), ctypes.byref(chosen), None, None)
    except (AttributeError, OSError) as error:
        raise NativeDialogUnavailable("Native exit confirmation unavailable") from error
    if status != 0:
        raise NativeDialogUnavailable("Native exit confirmation unavailable")
    return chosen.value == 6
