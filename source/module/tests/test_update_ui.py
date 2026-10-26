import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QObject, QSettings, QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox
from update_ui import UpdateManager
from update_core import Release, UpdateError


class Controller(QObject):
    def __init__(self,store):
        super().__init__()
        self.window=QWidget();self.store=store;self._stopping=False
        self.stop=Mock()


class UpdateUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.controller=Controller(QSettings(str(Path(self.temp.name)/'s.ini'),QSettings.Format.IniFormat))
        self.manager=UpdateManager(self.controller,'0.7.7')
        self.release=Release('0.7.8','https://github.com/luttechan/Lexift/releases/tag/v0.7.8')

    def tearDown(self):
        self.manager._close_dialog();self.controller.window.hide()
        if self.manager.result_dialog:
            self.manager.result_dialog.hide(); self.manager.result_dialog.deleteLater()
        self.manager.deleteLater();self.controller.window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.qt.processEvents()

    def test_programmatic_progress_close_does_not_cancel_operation(self):
        self.manager._dialog('Checking')
        self.manager._close_dialog()
        self.assertFalse(self.manager.cancel_event.is_set())

    def test_manual_check_reports_remote_version_even_when_local_is_newer(self):
        self.manager._checked(Release('0.7.6',self.release.page))
        result = self.manager.result_dialog
        self.assertIn('0.7.6',result.versions.text())
        self.assertIn('0.7.7',result.versions.text())
        self.assertEqual(result.status.text(), '당신은 개발자입니다.')
        self.assertIsNone(result.install_button)

    def test_current_and_older_versions_have_distinct_status(self):
        self.manager._checked(Release('0.7.7',self.release.page))
        self.assertEqual(self.manager.result_dialog.status.text(), '최신 버전입니다.')
        self.manager._checked(self.release)
        self.assertEqual(self.manager.result_dialog.status.text(), '업데이트가 필요합니다.')
        self.assertIsNotNone(self.manager.result_dialog.install_button)

    def test_same_version_with_a_new_build_offers_the_hotfix(self):
        release=Release('0.7.7',self.release.page,build='a'*64)
        with patch('update_ui.installed_build',return_value='b'*64):self.manager._checked(release)
        self.assertEqual(self.manager.result_dialog.status.text(),'업데이트가 필요합니다.')
        self.assertIsNotNone(self.manager.result_dialog.install_button)

    def test_matching_build_does_not_repeat_the_compatibility_update(self):
        release=Release('0.7.7',self.release.page,build='a'*64)
        with patch('update_ui.installed_build',return_value='a'*64):self.manager._checked(release)
        self.assertEqual(self.manager.result_dialog.status.text(),'최신 버전입니다.')
        self.assertIsNone(self.manager.result_dialog.install_button)

    def test_progress_and_results_do_not_block_other_windows(self):
        self.manager._dialog('Checking')
        self.assertEqual(self.manager.dialog.windowModality(), Qt.WindowModality.NonModal)
        self.manager._checked(Release('0.7.7',self.release.page))
        self.assertEqual(self.manager.result_dialog.windowModality(), Qt.WindowModality.NonModal)
        self.assertIsNone(self.qt.activeModalWidget())

    def test_automatic_checks_are_quiet_without_new_version(self):
        self.manager.automatic=True
        self.manager._checked(Release('0.7.7',self.release.page))
        self.assertIsNone(self.manager.result_dialog)

    def test_duplicate_checks_do_not_launch_more_workers(self):
        self.manager.busy=True
        with patch('update_ui.threading.Thread') as worker:
            self.manager.check()
        worker.assert_not_called()

    def test_background_worker_delivers_manual_result_without_cancelling(self):
        from PySide6.QtTest import QTest
        import time
        with patch('update_ui.latest_release',return_value=Release('0.7.6',self.release.page)):
            self.manager.check()
            deadline=time.monotonic()+3
            while self.manager.busy and time.monotonic()<deadline:
                QTest.qWait(10)
        self.assertFalse(self.manager.busy)
        self.assertFalse(self.manager.cancel_event.is_set())
        self.assertIn('0.7.6', self.manager.result_dialog.versions.text())

    def test_automatic_notification_once_per_version_manual_check_still_works(self):
        self.manager.automatic=True
        with patch.object(self.manager,'_result') as ask:
            self.manager._checked(self.release)
            self.manager._checked(self.release)
            self.manager.automatic=False
            self.manager._checked(self.release)
        self.assertEqual(ask.call_count,2)
        self.assertFalse(self.manager.busy)

    def test_source_launch_opens_page_only_after_user_confirmation(self):
        with patch('update_ui.QDesktopServices.openUrl') as open_page:
            self.manager._checked(self.release)
            open_page.assert_not_called()
            self.manager.result_dialog.install_button.click()
        open_page.assert_called_once()

    def test_no_confirmation_no_download(self):
        with patch.object(self.manager,'_download') as download:
            self.manager._checked(self.release)
        download.assert_not_called()

    def test_cancelled_preparation_never_starts_helper(self):
        job=Path(self.temp.name)/'job';job.mkdir()
        self.manager.cancel_event.set()
        with patch('update_ui.subprocess.Popen') as spawn:
            self.manager._prepared(job)
        import time
        deadline = time.monotonic() + 2
        while job.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(job.exists())
        spawn.assert_not_called()

    def test_network_error_never_claims_latest_and_background_error_is_quiet(self):
        with patch('update_ui.logging.warning'):
            self.manager.automatic=True;self.manager._failed(UpdateError('offline'))
            self.assertIsNone(self.manager.result_dialog)
            self.manager.automatic=False;self.manager._failed(UpdateError('offline'))
        self.assertIn('인터넷 연결', self.manager.result_dialog.status.text())
        self.assertNotIn('최신 버전입니다.', self.manager.result_dialog.status.text())
