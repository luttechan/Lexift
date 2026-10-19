import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication
import app
from layout_profiles import create_layout


class SlotWheelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        layouts = [create_layout(code) for code in (0x0412,0x0411,0x0409)]
        self.slots = [dict(hkl=layouts[0].hkl,mode='ko_hangul',name=str(i)) for i in range(15)]
        with patch.object(app,'available_layouts',return_value=layouts):
            self.editor = app.SlotEditor(self.slots)
        self.editor.resize(850,500)
        self.editor.show()
        self.qt.processEvents()
        self.bar = self.editor.scroll.verticalScrollBar()
        self.bar.setValue(80)
        self.row = self.editor.list_layout.itemAt(2).widget()

    def tearDown(self):
        self.editor.hide()
        self.editor.deleteLater()
        self.qt.processEvents()

    def wheel(self, widget, *, angle=0, pixels=0):
        pos = widget.rect().center()
        event = QWheelEvent(QPointF(pos),QPointF(widget.mapToGlobal(pos)),
                            QPoint(0,pixels),QPoint(0,angle),Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
        self.qt.sendEvent(widget,event)
        self.qt.processEvents()

    def test_wheel_over_both_closed_fields_scrolls_without_changing_slots(self):
        before = [dict(slot) for slot in self.editor.slots]
        revision = self.editor._list_revision
        for combo in self.row.findChildren(app.SlotComboBox):
            position = self.bar.value()
            self.wheel(combo,angle=-120)
            self.assertGreater(self.bar.value(),position)
        self.assertEqual(self.editor.slots,before)
        self.assertEqual(self.editor._list_revision,revision)

    def test_pixel_delta_tracks_actual_content_offset_without_row_snapping(self):
        viewport = self.editor.scroll.viewport()
        before = self.row.mapTo(viewport,QPoint()).y()
        self.wheel(viewport,pixels=-25)
        self.assertEqual(self.bar.value(),105)
        self.assertEqual(self.row.mapTo(viewport,QPoint()).y(),before-25)
        self.wheel(viewport,pixels=-7)
        self.wheel(viewport,pixels=-11)
        self.assertEqual(self.bar.value(),123)

    def test_scrollbar_preserves_partial_row_positions(self):
        for value in (101,137,243):
            self.bar.setValue(value)
            self.qt.processEvents()
            self.assertEqual(self.bar.value(),value)
            self.assertEqual(self.editor.list_host.y(),-value)
