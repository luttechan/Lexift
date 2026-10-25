"""Static safeguards for accidentally replacing the Lexift v0.6 design."""
from pathlib import Path
import unittest

APP = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')


class OriginalDesignTests(unittest.TestCase):
    def test_original_sidebar(self):
        self.assertIn('sidebar.setFixedWidth(226)', APP)
        self.assertIn('for text in (tr("대시보드"), tr("입력기 슬롯"), tr("일반 설정"), tr("프로그램 정보"),tr(\'사용자 사전\'))', APP)

    def test_original_dashboard_and_cards(self):
        self.assertIn('def _make_dashboard(self)', APP)
        self.assertIn('self.preview.addWidget(card, i//3, i%3)', APP)
        self.assertIn('self.resize(1020, 690)', APP)
        self.assertIn('self.setMinimumSize(850, 560)', APP)

    def test_original_charcoal_theme(self):
        self.assertIn('QWidget#window { background:#0D0E11; }', APP)
        self.assertIn('QFrame#side { background:#111216;', APP)
        self.assertIn('QFrame#panel { background:#17191E;', APP)
        self.assertIn('QFrame#tile { background:#1C1F25;', APP)

    def test_features_added_without_removing_pages(self):
        self.assertIn('self.window.shortcut_changed.connect(self.change_shortcut)', APP)
        self.assertIn('self.dashboard_shortcut.setText(binding.title)', APP)
        self.assertIn('self.special_list', APP)
        # Verify the destination, rather than the source's quotes/formatting.
        import app
        from types import SimpleNamespace
        from unittest.mock import Mock
        from PySide6.QtWidgets import QApplication
        from i18n import tr
        qt=QApplication.instance() or QApplication([])
        controller=SimpleNamespace(**{name:Mock() for name in
            ('show_overlay','show_window','check_updates','request_quit','set_enabled')})
        controller._style_tray_menu=lambda:app.LexiftController._style_tray_menu(controller)
        app.LexiftController._create_tray_menu(controller)
        try:
            next(a for a in controller.tray_menu.actions() if a.text()==tr('설정')).trigger()
            controller.show_window.assert_called_once_with(2)
        finally:controller.tray_menu.deleteLater();qt.processEvents()


if __name__ == '__main__':
    unittest.main()
