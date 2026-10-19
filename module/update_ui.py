"""Responsive update checks and explicitly confirmed portable installation."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout

from i18n import tr, text_font_family
from update_core import UpdateCancelled, UpdateError, version_number, updater_path
from update_network import isolated_check as latest_release, isolated_download
from update_apply import cache_root, plain_tree


class UpdateProgress(QDialog):
    """Owned progress window, without QProgressDialog's delayed-show timers."""
    def __init__(self, text, determinate, parent=None):
        super().__init__(parent)
        self.setObjectName("updateProgress")
        self.setStyleSheet('QDialog#updateProgress { background:#17191E; color:#EBEBEF; } '
                          'QLabel { color:#EBEBEF; } '
                          'QProgressBar { border:1px solid #393E47; border-radius:4px; '
                          'background:#202329; color:#EBEBEF; text-align:center; } '
                          'QProgressBar::chunk { background:#667D9C; }'
                          f'QWidget {{ font-family:"{text_font_family(text)}"; }}')
        self.can_cancel = True
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        self.label = QLabel(text)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100 if determinate else 0)
        self.cancel_button = QPushButton(tr("취소"))
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        layout.addWidget(self.cancel_button)

    def setLabelText(self, text):
        self.label.setText(text)

    def setValue(self, value):
        self.bar.setValue(value)

    def setCancelButton(self, button):
        self.can_cancel = False
        self.cancel_button.hide()

    def reject(self):
        if self.can_cancel:
            super().reject()

    def closeEvent(self, event):
        if self.can_cancel:
            super().closeEvent(event)
        else:
            event.ignore()


class UpdateResult(QDialog):
    def __init__(self, current, remote, status, action_text=None, action=None, parent=None):
        super().__init__(parent)
        self.setObjectName('updateResult')
        self.setWindowTitle(tr('업데이트 확인'))
        self.setMinimumWidth(390)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setStyleSheet('QDialog#updateResult { background:#17191E; } '
                          'QLabel { color:#EBEBEF; }'
                          f'QWidget {{ font-family:"{text_font_family(status)}"; }}')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(15)
        self.versions = QLabel(f"{tr('현재 버전')} : {current}\n{tr('배포 버전')} : {remote}")
        self.versions.setTextFormat(Qt.TextFormat.PlainText)
        self.status = QLabel(status)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.versions)
        layout.addWidget(self.status)
        self.install_button = None
        if action is not None:
            self.install_button = QPushButton(action_text)
            self.install_button.clicked.connect(action)
            layout.addWidget(self.install_button)
        close = QPushButton(tr('닫기'))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class UpdateManager(QObject):
    checked = Signal(object)
    prepared = Signal(object)
    failed = Signal(object)
    progress = Signal(int)

    def __init__(self, controller, version):
        super().__init__(controller)
        self.controller = controller
        self.version = version
        self.busy = False
        self.automatic = False
        self.cancel_event = threading.Event()
        self.dialog = None
        self.job_dir = None
        self.helper = None
        self.result_dialog = None
        self.checked.connect(self._checked)
        self.prepared.connect(self._prepared)
        self.failed.connect(self._failed)
        self.progress.connect(self._progress)

    def _dialog(self, text, determinate=False):
        self._close_dialog()
        # A language change may replace the main window during a modeless check.
        self.dialog = UpdateProgress(text, determinate)
        self.dialog.setWindowTitle(tr("업데이트 확인"))
        self.dialog.setWindowModality(Qt.WindowModality.NonModal)
        self.dialog.rejected.connect(self.cancel)
        self.dialog.show()

    def _close_dialog(self):
        if self.dialog is not None:
            self.dialog.rejected.disconnect(self.cancel)
            self.dialog.hide()
            self.dialog.deleteLater()
            self.dialog = None

    def check(self, automatic=False):
        if self.busy or self.controller._stopping:
            return
        self.busy = True
        if self.result_dialog is not None:
            self.result_dialog.hide()
            self.result_dialog.deleteLater()
            self.result_dialog = None
        self.automatic = automatic
        self.cancel_event = threading.Event()
        if not automatic:
            self._dialog(tr("업데이트를 확인하는 중..."))

        def work():
            try:
                release = latest_release(self.cancel_event)
                if self.cancel_event.is_set():
                    raise UpdateCancelled("Cancelled")
                self.checked.emit(release)
            except Exception as error:
                self.failed.emit(error)
        threading.Thread(target=work, daemon=True, name="KanaShift-ReleaseCheck").start()

    @Slot(object)
    def _checked(self, release):
        self._close_dialog()
        self.busy = False
        if self.cancel_event.is_set() or self.controller._stopping:
            return
        remote, current = version_number(release.version), version_number(self.version)
        if remote <= current:
            if not self.automatic:
                self._result(release.version, tr('최신 버전입니다.') if remote == current
                             else tr('당신은 개발자입니다.'))
            return
        store = self.controller.store
        if self.automatic and store.value("updates/notified_version", "", str) == release.version:
            return
        store.setValue("updates/notified_version", release.version)
        packaged = getattr(sys, "frozen", False)
        can_install = bool(packaged and release.asset_url and
                           updater_path(Path(sys.executable).parent).is_file())
        def install():
            if self.busy or self.controller._stopping:
                return
            self.result_dialog.accept()
            if can_install:
                self._download(release)
            else:
                QDesktopServices.openUrl(QUrl(release.page))
        self._result(release.version, tr('업데이트가 필요합니다.'),
                     tr('다운로드 및 설치') if can_install else tr('다운로드 페이지 열기'), install)

    def _result(self, remote, status, action_text=None, action=None):
        if self.result_dialog is not None:
            self.result_dialog.hide()
            self.result_dialog.deleteLater()
        self.result_dialog = UpdateResult(self.version, remote, status, action_text, action)
        self.result_dialog.show()

    def _download(self, release):
        self.busy = True
        self.automatic = False
        self.cancel_event = threading.Event()
        self._dialog(tr("다운로드 및 파일 확인 중..."), determinate=True)
        target = Path(sys.executable).parent

        def work():
            job_dir = None
            try:
                # Fail before download when the installation is not writable.
                probe = target / (".kanashift-write-" + uuid.uuid4().hex)
                with probe.open("xb"):
                    pass
                probe.unlink()
                base = cache_root()
                base.mkdir(parents=True, exist_ok=True)
                job_dir = base / uuid.uuid4().hex
                job_dir.mkdir()
                plain_tree(job_dir)
                payload = isolated_download(release, job_dir, self.cancel_event, self.progress.emit)
                if self.cancel_event.is_set():
                    raise UpdateCancelled("Cancelled")
                # The helper runs outside the directory whose DLLs it replaces.
                shutil.copy2(updater_path(target), job_dir / "KanaShiftUpdater.exe")
                job = dict(product="KanaShift", nonce=job_dir.name, version=release.version,
                           target=str(target), payload=str(payload), parent_pid=os.getpid())
                (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
                self.prepared.emit(job_dir)
            except Exception as error:
                if job_dir is not None:
                    shutil.rmtree(job_dir, ignore_errors=True)
                self.failed.emit(error)
        threading.Thread(target=work, daemon=True, name="KanaShift-UpdateDownload").start()

    @Slot(int)
    def _progress(self, value):
        if self.dialog is not None:
            self.dialog.setValue(value)

    @Slot(object)
    def _prepared(self, job_dir):
        if self.cancel_event.is_set() or self.controller._stopping:
            threading.Thread(target=shutil.rmtree, args=(job_dir,),
                             kwargs={'ignore_errors': True}, daemon=True).start()
            self._close_dialog()
            self.busy = False
            return
        try:
            self.job_dir = job_dir
            self.helper = subprocess.Popen([str(job_dir / "KanaShiftUpdater.exe"), "--job", str(job_dir / "job.json")],
                cwd=job_dir, close_fds=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self._handoff_deadline = time.monotonic() + 60
            self.dialog.setLabelText(tr("파일 교체를 준비하는 중..."))
            self.dialog.setCancelButton(None)
            self._poll_helper()
        except Exception as error:
            self._failed(error)

    def _poll_helper(self):
        try:
            ready = self.job_dir / "helper-ready"
            if ready.exists() and ready.read_text(encoding="ascii") == self.job_dir.name:
                self._close_dialog()
                self.controller.stop()  # Installation was already confirmed.
                return
            if self.helper.poll() is not None:
                detail = self.job_dir / "error.log"
                raise UpdateError(detail.read_text(encoding="utf-8") if detail.exists() else "Update helper could not start")
            if time.monotonic() > self._handoff_deadline:
                # Helper has not claimed the parent; no files have been replaced.
                self.helper.terminate()
                raise UpdateError("Update helper timed out")
            QTimer.singleShot(100, self._poll_helper)
        except Exception as error:
            self._failed(error)

    @Slot(object)
    def _failed(self, error):
        self._close_dialog()
        self.busy = False
        if isinstance(error, UpdateCancelled) or self.cancel_event.is_set() or self.controller._stopping:
            return
        logging.warning("Update check/install failed: %s", error)
        if not self.automatic:
            self._result('—', tr('업데이트 실패') + '\n' + str(error))

    def cancel(self):
        self.cancel_event.set()
