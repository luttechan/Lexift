"""Reusable application notifications without the Windows default balloon sound."""
from PySide6.QtCore import Qt,QTimer,Signal
from PySide6.QtGui import QCursor,QFont
from PySide6.QtWidgets import QApplication,QFrame,QLabel,QSystemTrayIcon,QVBoxLayout
from i18n import text_font_family
from notification_sound import notify_event

class NotificationToast(QFrame):
    clicked=Signal()
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
                           Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName('notification')
        self.setStyleSheet('QFrame#notification {background:#182234;border:1px solid #354963;border-radius:12px;} QLabel {color:#fff;background:transparent;border:0;}')
        layout=QVBoxLayout(self);layout.setContentsMargins(18,14,18,14)
        self.title=QLabel();self.message=QLabel()
        for item in (self.title,self.message):
            item.setTextFormat(Qt.TextFormat.PlainText);item.setWordWrap(True);layout.addWidget(item)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.hide)
    def present(self,title,message,duration):
        self.title.setText(title);self.message.setText(message)
        for item in (self.title,self.message):item.setFont(QFont(text_font_family(item.text()),10))
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area=screen.availableGeometry();self.setFixedWidth(min(400,area.width()-24))
        self.adjustSize();self.move(area.right()-self.width()-16,area.bottom()-self.height()-16)
        self.show();self.timer.start(max(1000,min(int(duration),10000)))
    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.hide();self.clicked.emit()
        super().mouseReleaseEvent(event)

class NotificationTray(QSystemTrayIcon):
    def __init__(self,icon,parent=None):
        super().__init__(icon,parent);self.toast=None
    def showMessage(self,title,message,icon=QSystemTrayIcon.MessageIcon.Information,msecs=10000):
        if self.toast is None:
            self.toast=NotificationToast();self.toast.clicked.connect(self.messageClicked.emit)
            self.destroyed.connect(self.toast.deleteLater)
        self.toast.present(title,message,msecs);notify_event()
    def hide_notification(self):
        if self.toast:self.toast.hide();self.toast.timer.stop()
