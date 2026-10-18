from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QFontMetrics
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class CursorIndicator(QWidget):
    DURATION_MS = 1000

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("cursorIndicator")
        self.setStyleSheet(
            "QWidget#cursorIndicator { background:#20242C; border:1px solid #66758A; }"
            "QLabel { color:#F3F4F7; background:transparent; border:0; font-size:13px; }"
        )
        body = QVBoxLayout(self)
        body.setContentsMargins(10, 6, 10, 6)
        self.text = QLabel()
        self.text.setTextFormat(Qt.TextFormat.PlainText)
        body.addWidget(self.text)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.dismiss)

    def show_language(self, text: str):
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor) or QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        budget = max(1, min(300, rect.width() - 20))
        self.text.setText(QFontMetrics(self.text.font()).elidedText(
            text, Qt.TextElideMode.ElideRight, budget))
        self.adjustSize()
        x, y = cursor.x() + 18, cursor.y() + 24
        if x + self.width() > rect.right() + 1:
            x = cursor.x() - self.width() - 12
        if y + self.height() > rect.bottom() + 1:
            y = cursor.y() - self.height() - 12
        self.move(max(rect.left(), min(x, rect.right() - self.width() + 1)),
                  max(rect.top(), min(y, rect.bottom() - self.height() + 1)))
        self.show()
        # One owned timer: a previous notification cannot hide the next one.
        self.timer.start(self.DURATION_MS)

    def dismiss(self):
        self.timer.stop()
        self.hide()
