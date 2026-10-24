import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QPoint, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import app
from layout_profiles import create_layout


class AddedSlotVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        layout = create_layout(0x0412)
        slots = [dict(hkl=layout.hkl, mode='ko_hangul', name=str(i)) for i in range(6)]
        with patch.object(app, 'available_layouts', return_value=[layout]):
            self.editor = app.SlotEditor(slots)
        self.editor.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.editor.resize(850, 420)
        self.editor.show()
        QTest.qWait(30)
        bar = self.editor.scroll.verticalScrollBar()
        bar.setValue(bar.maximum()//2)

    def tearDown(self):
        self.editor.hide(); self.editor.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.qt.processEvents()

    def assert_last_row_visible(self):
        row = self.editor.list_layout.itemAt(len(self.editor.slots)-1).widget()
        viewport = self.editor.scroll.viewport()
        top = row.mapTo(viewport, QPoint(0, 0)).y()
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(top + row.height(), viewport.height())

    def test_add_reveals_new_row_from_middle_of_list(self):
        before = self.editor.scroll.verticalScrollBar().value()
        self.editor.add_slot()
        QTest.qWait(30)
        self.assertGreater(self.editor.scroll.verticalScrollBar().value(), before)
        self.assert_last_row_visible()

    def test_rapid_adds_reveal_the_final_row(self):
        for _ in range(9):
            self.editor.add_slot()
        QTest.qWait(30)
        self.assertEqual(len(self.editor.slots), 15)
        self.assert_last_row_visible()

    def test_deleted_row_invalidates_pending_scroll(self):
        self.editor.add_slot()
        self.editor.delete_slot(6)
        with patch.object(self.editor.scroll, 'ensureWidgetVisible') as reveal:
            QTest.qWait(30)
        reveal.assert_not_called()
