"""Display the actual Caps Lock toggle state without consuming keyboard input."""
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QObject,QTimer,Qt,Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication,QLabel


def caps_lock_state():
    from ime_windows import user32
    user32.GetKeyState.argtypes=[ctypes.c_int]
    user32.GetKeyState.restype=ctypes.c_short
    return bool(user32.GetKeyState(0x14)&1)


def active_screen():
    """Use the foreground window's monitor, mapped to Qt's logical geometry."""
    from ime_windows import user32,MonitorInfo
    user32.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD]
    user32.MonitorFromWindow.restype=wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype=wintypes.BOOL
    monitor=user32.MonitorFromWindow(user32.GetForegroundWindow(),2)
    info=MonitorInfo();info.size=ctypes.sizeof(info)
    if monitor and user32.GetMonitorInfoW(monitor,ctypes.byref(info)):
        for screen in QApplication.screens():
            if screen.name().casefold()==info.device.casefold():return screen
    return QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()


class CapsLockIndicator(QObject):
    changed=Signal(bool)

    def __init__(self,parent=None,read_state=None,get_screen=None):
        super().__init__(parent)
        self.read_state=read_state or caps_lock_state
        self.get_screen=get_screen or active_screen
        self.toast=None;self.state=None
        self.timer=QTimer(self);self.timer.setInterval(80)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.poll)
        self.hide_timer=QTimer(self);self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(1000);self.hide_timer.timeout.connect(self.hide)
        self.set_enabled(True)

    def set_enabled(self,enabled):
        self.enabled=bool(enabled)
        self.timer.stop();self.hide()
        if enabled:
            self.state=bool(self.read_state())
            self.timer.start()

    def poll(self):
        if not self.enabled:return
        current=bool(self.read_state())
        if current==self.state:return
        self.state=current
        self.show_state(current);self.changed.emit(current)

    def show_state(self,enabled):
        if self.toast is None:
            self.toast=QLabel()
            self.toast.setWindowFlags(Qt.WindowType.ToolTip|Qt.WindowType.FramelessWindowHint|
                Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus|
                Qt.WindowType.WindowTransparentForInput)
            self.toast.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.toast.setTextFormat(Qt.TextFormat.PlainText)
            self.toast.setStyleSheet('background:#182234;color:#ffffff;border:1px solid #354963;'
                'border-radius:12px;padding:18px 32px;font-family:"Malgun Gothic";font-size:22px;font-weight:700;')
            self.destroyed.connect(self.toast.deleteLater)
        self.toast.setText('Caps Lock  '+('ON' if enabled else 'OFF'))
        self.toast.adjustSize()
        screen=self.get_screen()
        if screen:
            bounds=self.toast.rect();bounds.moveCenter(screen.geometry().center())
            self.toast.move(bounds.topLeft())
        self.toast.show();self.hide_timer.start()

    def hide(self):
        self.hide_timer.stop()
        if self.toast:self.toast.hide()

    def stop(self):
        self.set_enabled(False)
