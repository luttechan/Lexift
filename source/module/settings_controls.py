"""Dropdowns that require an explicit selection, rather than an accidental wheel."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox


class SettingsComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)
        self.view().setUniformItemSizes(True)

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            # Ignore even when focused; Qt propagates this to the scroll viewport.
            event.ignore()
