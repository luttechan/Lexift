"""Qt's stock button labels otherwise follow the Windows/Qt locale."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox as QtMessageBox
from i18n import tr, text_font_family


class QMessageBox(QtMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)

    def setStandardButtons(self, buttons):
        super().setStandardButtons(buttons)
        for value, key in ((self.StandardButton.Ok, '확인'),
                           (self.StandardButton.Yes, '예'),
                           (self.StandardButton.No, '아니요'),
                           (self.StandardButton.Cancel, '취소')):
            button = self.button(value)
            if button is not None:
                button.setText(tr(key))

    @classmethod
    def _show(cls, icon, parent, title, text, buttons, default):
        dialog = cls(parent)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStyleSheet(f'QWidget {{ font-family:"{text_font_family(text)}"; }}')
        dialog.setStandardButtons(buttons)
        if default != cls.StandardButton.NoButton:
            dialog.setDefaultButton(default)
        from notification_sound import notify_event
        notify_event()
        try:
            dialog.exec()
            clicked = dialog.clickedButton()
            return dialog.standardButton(clicked) if clicked else cls.StandardButton.NoButton
        finally:
            dialog.deleteLater()

    @classmethod
    def information(cls, parent, title, text, buttons=QtMessageBox.StandardButton.Ok,
                    defaultButton=QtMessageBox.StandardButton.NoButton):
        return cls._show(cls.Icon.Information, parent, title, text, buttons, defaultButton)

    @classmethod
    def warning(cls, parent, title, text, buttons=QtMessageBox.StandardButton.Ok,
                defaultButton=QtMessageBox.StandardButton.NoButton):
        return cls._show(cls.Icon.Warning, parent, title, text, buttons, defaultButton)

    @classmethod
    def critical(cls, parent, title, text, buttons=QtMessageBox.StandardButton.Ok,
                 defaultButton=QtMessageBox.StandardButton.NoButton):
        return cls._show(cls.Icon.Critical, parent, title, text, buttons, defaultButton)

    @classmethod
    def question(cls, parent, title, text,
                 buttons=QtMessageBox.StandardButton.Yes | QtMessageBox.StandardButton.No,
                 defaultButton=QtMessageBox.StandardButton.NoButton):
        return cls._show(cls.Icon.Question, parent, title, text, buttons, defaultButton)
