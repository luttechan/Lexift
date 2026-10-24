from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import ctypes
import winreg
import os
import sys
import time
from pathlib import Path

# Suppress only the non-fatal ICC-profile description warning.
os.environ.setdefault("QT_LOGGING_RULES", "qt.gui.icc.warning=false")
# DirectWrite's system font collection can map thousands of unrelated font
# files on font-heavy Windows installations. Lexift uses static UI fonts.
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=gdi")

from PySide6.QtCore import QObject, Qt, QSettings, QTimer, Signal, QSize, QUrl, QEventLoop, QPoint
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QFont, QFontDatabase, QFontMetrics, QIcon, QImage, QPainter, QPen, QPixmap, QPixmapCache, QRegion
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLayout, QLineEdit, QMenu, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QSystemTrayIcon, QVBoxLayout,
    QWidget,
)

from hotkeys_windows import HotkeyBinding, MODES, MODE_LABELS, KEY_LABELS
from isolated_hotkeys import CapsQHook, OverlayNavigationHook, service as keyboard_service
from credits_static import get_special_thanks
from i18n import LANGUAGES, SUPPORTED, set_language, language, tr, tr_count, tr_hint, tr_notify, text_font_family, error_text, load_saved_language
from localized_dialogs import QMessageBox
from native_language_dialog import choose_ui_language, confirm_quit, NativeDialogUnavailable
from cursor_indicator import CursorIndicator
from update_ui import UpdateManager
from update_apply import mark_ready
from ime_windows import (
    IMEError, current_hkl, cycle_windows_language, foreground_target,
    get_target_window, japanese_fallback_key, japanese_matches, japanese_set,
    korean_is_hangul, korean_set, korean_toggle_key, request_hkl, target_is_foreground,
    ime_native_status, ime_set_native, ime_toggle_native, current_language, LANG_KO,
)
from grid_navigation import move_selection
from layout_profiles import (
    LayoutInfo, available_layouts, default_name, first_run_slots,
    hkl_number, hkl_string, installed_slots, mode_options,
    needs_first_run_setup, sanitized_slots, editable_slots, MAX_SLOTS, preferred_mode,
)

VERSION = "1.0.0"
ORGANIZATION = "LuteTools"
PRODUCT = "Lexift"
SELECTION_KEYS = "1234567890ABCDE"

# Malgun Gothic has Regular/Bold faces. Intermediate weights trigger expensive
# GDI style searches on font-heavy systems. Use the two supported weights.
# Qt renders all text; no custom drawn or scaled glyphs.
QSS = """
QWidget { color:#EBEBEF; font-family:"Malgun Gothic"; font-size:13px; background:transparent; }
QWidget#window { background:#0D0E11; }
QFrame#side { background:#111216; border-right:1px solid #282A30; }
QFrame#brandMark { background:transparent; border:0; }
QLabel#brand { font-weight:700; font-size:19px; color:#FFFFFF; }
QLabel#logoCaption, QLabel#muted, QLabel#subtitle { color:#8A8D98; }
QLabel#pageTitle { color:#F6F6F8; font-size:27px; font-weight:700; }
QLabel#section { color:#E3E3E8; font-size:15px; font-weight:700; }
QLabel#small { color:#9699A3; font-size:11px; }
QLabel#metric { color:#F2F2F7; font-size:21px; font-weight:700; }
QFrame#panel { background:#17191E; border:1px solid #2A2D35; border-radius:14px; }
QFrame#surface { background:#13151A; border:1px solid #282B32; border-radius:12px; }
QFrame#slotRow { background:#17191E; border:1px solid #2B2E35; border-radius:13px; }
QFrame#hud { background:#14161B; border:1px solid #393D46; border-radius:20px; }
QFrame#tile { background:#1C1F25; border:1px solid #32353F; border-radius:13px; }
QFrame#tile:hover { background:#252932; border-color:#575D6B; }
QFrame#tile[selected="true"] { background:#29303D; border:1px solid #9BAEC8; }
QLabel#badge { background:#292F39; border-radius:7px; padding:5px 9px; color:#B8C7D8; font-size:11px; font-weight:700; }
QLabel#tileCode { color:#B2C5E1; font-size:13px; font-weight:700; }
QLabel#tileName { color:#F3F4F7; font-size:16px; font-weight:700; }
QLabel#tileDetail { color:#999DA9; font-size:11px; }
QLabel#hintKey { background:#292D35; color:#C1C4CC; border:1px solid #3D4149; border-radius:6px; padding:4px 8px; }
QPushButton { background:#24272E; color:#E7E9EE; border:1px solid #383D46; border-radius:9px; padding:9px 13px; min-height:20px; }
QPushButton:hover { background:#30343D; border-color:#505865; }
QPushButton:pressed { background:#393F49; }
QPushButton:disabled { color:#777B86; background:#1B1D22; border-color:#2B2F35; }
QPushButton#primary { background:#DFE5EF; color:#10141B; font-weight:700; border:1px solid #DFE5EF; }
QPushButton#primary:hover { background:#FFFFFF; border-color:#FFFFFF; }
QPushButton#nav { background:transparent; border:0; color:#B8BBC6; text-align:left; min-height:25px; padding:10px 14px; font-weight:400; }
QPushButton#nav:hover { background:#1C1F25; color:#F0F0F3; }
QPushButton#nav[active="true"] { background:#262B33; color:#FFFFFF; border-left:2px solid #A9BACF; border-top-left-radius:0; border-bottom-left-radius:0; font-weight:400; }
QPushButton#ghost { background:transparent; border:1px solid #363A43; }
QPushButton#danger { background:transparent; border:1px solid #4E3536; color:#E0A4A7; }
QPushButton#toggle:checked { background:#29303D; border-color:#9BAEC8; }
QLineEdit, QComboBox { background:#202329; color:#F1F2F5; border:1px solid #393E47; border-radius:8px; padding:8px 10px; min-height:21px; selection-background-color:#566982; }
QLineEdit:focus, QComboBox:focus { border:1px solid #A2B4CC; }
QComboBox QAbstractItemView { background:#1B1D22; color:#ECEEF3; selection-background-color:#344356; border:1px solid #414650; }
QCheckBox { color:#C9CBD1; spacing:11px; }
QScrollArea { background:transparent; border:0; }
QScrollBar:vertical { background:#13151A; width:8px; margin:1px; }
QScrollBar::handle:vertical { background:#444952; border-radius:4px; min-height:24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QLabel#overlayTitle { font-size:23px; font-weight:700; color:#FFFFFF; }
QLabel#overlaySub { font-size:12px; color:#989CA7; }
"""


def local_font_path() -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / "Style" / "malgun.ttf"


def choose_font(app: QApplication) -> None:
    """Prefer the local font file; Qt still initializes its platform font database."""
    path = local_font_path()
    if path.is_file() and app.property("kanashiftLocalFontPath") != str(path):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            app.setProperty("kanashiftLocalFontPath", str(path))
            app.setProperty("kanashiftLocalFontId", font_id)
        else:
            logging.warning("Could not load local font: %s; using the Windows font", path)
    family = "Malgun Gothic"
    font = QFont(family, 10)
    font.setWeight(QFont.Weight.Normal)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    # Native popup animations delay menus even after their contents are ready.
    for effect in (Qt.UIEffect.UI_AnimateCombo, Qt.UIEffect.UI_AnimateMenu,
                   Qt.UIEffect.UI_FadeMenu):
        app.setEffectEnabled(effect, False)


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            for name in (PRODUCT,'KanaShift'):
                try:
                    if winreg.QueryValueEx(key,name)[0]:return True
                except FileNotFoundError:pass
            return False
    except OSError:
        return False


def set_startup_enabled(enabled: bool) -> None:
    """Manage per-user startup only. No administrator permission required."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if not enabled:
            for name in (PRODUCT,'KanaShift'):
                try:winreg.DeleteValue(key,name)
                except FileNotFoundError:pass
            return
        if getattr(sys, "frozen", False):
            command = f'"{sys.executable}" --background'
        else:
            interpreter = Path(sys.executable)
            pythonw = interpreter.with_name("pythonw.exe")
            if pythonw.exists():
                interpreter = pythonw
            entry = Path(__file__).resolve().parent.parent / "launch.pyw"
            command = f'"{interpreter}" "{entry}" --background'
        winreg.SetValueEx(key, PRODUCT, 0, winreg.REG_SZ, command)
        try:winreg.DeleteValue(key,'KanaShift')
        except FileNotFoundError:pass


def icon() -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#DDE5F1"))
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    painter.setPen(QPen(QColor("#161A20"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(22, 16, 22, 48)
    painter.drawLine(22, 48, 44, 48)
    painter.end()
    return QIcon(pix)


def apply_text_font(widget, text):
    family = text_font_family(text)
    if widget.property('kanashiftTextFamily') != family:
        widget.setProperty('kanashiftTextFamily', family)
        if family != "Malgun Gothic" or widget.styleSheet():
            widget.setStyleSheet(f'font-family:"{family}";')


def label(text: str, kind: str = "", *, wrap: bool = False) -> QLabel:
    w = QLabel(text)
    apply_text_font(w, text)
    # Profile names are user text, never HTML or external image references.
    w.setTextFormat(Qt.TextFormat.PlainText)
    if kind:
        w.setObjectName(kind)
    w.setWordWrap(wrap)
    return w


def button(text: str, action=None, kind: str = "") -> QPushButton:
    b = QPushButton(text)
    apply_text_font(b, text)
    if kind:
        b.setObjectName(kind)
    if action:
        b.clicked.connect(action)
    return b


def brand_mark(width=176, height=58, *, dark=True):
    """Adapt the original wordmark to the interface without changing the file."""
    panel = QFrame()
    panel.setObjectName('brandMark')
    panel.setFixedSize(width,height)
    panel.setAccessibleName('Lexift')
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0,0,0,0)
    mark = QLabel()
    mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
    key = f'Lexift/wordmark/{width}/{height}/{"dark" if dark else "light"}'
    pixmap = QPixmapCache.find(key)
    if pixmap is None:
        path = Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent)) / 'Style/Lexift_black.png'
        original = QImage(str(path))
        if dark:
            # Invert RGB only: transparent margins and antialiasing stay intact.
            original.invertPixels(QImage.InvertMode.InvertRgb)
        pixmap = QPixmap.fromImage(original).scaled(width,height,
                    Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
        if not pixmap.isNull():
            QPixmapCache.insert(key,pixmap)
    if pixmap is not None and not pixmap.isNull():
        mark.setPixmap(pixmap)
    else:
        mark.setText('Lexift')
        mark.setStyleSheet(f'color:{"#EBEBEF" if dark else "#10141B"};font-size:22px;font-weight:700;')
    mark.setAccessibleName('Lexift')
    layout.addWidget(mark)
    return panel


def clear_layout(layout: QVBoxLayout | QGridLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            child = item.layout()
            clear_layout(child)
            child.deleteLater()


def short_code(profile: dict[str, str], layout: LayoutInfo | None) -> str:
    if profile.get("mode") in ("ko_latin", "ime_latin"):
        return "EN"
    if layout:
        if layout.family == "korean":
            return "KO" if profile.get("mode") != "ko_latin" else "EN"
        if layout.family == "japanese":
            return "JA"
        if layout.family.startswith("chinese"):
            return "ZH"
        return (layout.tag.split("-")[0] or "--").upper()[:3]
    return "--"


def mode_label(layout: LayoutInfo | None, mode: str) -> str:
    family = layout.family if layout else "standard"
    return next((tr(text) for key, text in mode_options(layout or family) if key == mode), tr("입력기 전환"))


class LoadingWindow(QWidget):
    """Brief on-screen status while Windows layouts and tray initialize."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(320, 125)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        box = QFrame()
        box.setObjectName("hud")
        content = QVBoxLayout(box)
        content.setContentsMargins(25, 21, 25, 21)
        content.setSpacing(8)
        content.addWidget(label("Lexift", "section"))
        content.addWidget(label(tr("불러오는 중..."), "muted"))
        outer.addWidget(box)

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.center().x()-self.width()//2, area.center().y()-self.height()//2)


class SlotCard(QFrame):
    activated = Signal(object)

    def __init__(self, slot: dict[str, str], layout: LayoutInfo | None, number: int):
        super().__init__()
        self.slot = dict(slot)
        self.usable = layout is not None
        self.setObjectName("tile")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.usable else Qt.CursorShape.ArrowCursor)
        self.setMinimumHeight(115)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 15)
        root.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(label(short_code(slot, layout), "tileCode"))
        top.addStretch()
        shortcut = SELECTION_KEYS[number - 1] if 1 <= number <= MAX_SLOTS else str(number)
        top.addWidget(label(str(number) if shortcut == str(number) else f"{number} · {shortcut}", "hintKey"))
        root.addLayout(top)
        name = slot.get("name") or (default_name(layout, slot["mode"]) if layout else tr("사용할 수 없는 입력기"))
        title = label(name, "tileName")
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title.setWordWrap(False)
        self._name_label = title
        self._name_full = name
        root.addWidget(title)
        subtitle = f"{layout.tag}  ·  {mode_label(layout, slot['mode'])}" if layout else tr("설정에서 입력기를 다시 선택하세요")
        sub = label(subtitle, "tileDetail")
        sub.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        sub.setWordWrap(False)
        self._detail_label = sub
        self._detail_full = subtitle
        root.addWidget(sub)
        self.setEnabled(self.usable)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Elide strings inside the tile; never expand a dialog to fit long names.
        usable = max(90, self.width() - 36)
        self._name_label.setText(QFontMetrics(self._name_label.font()).elidedText(
            self._name_full, Qt.TextElideMode.ElideRight, usable))
        self._detail_label.setText(QFontMetrics(self._detail_label.font()).elidedText(
            self._detail_full, Qt.TextElideMode.ElideRight, usable))

    def selected(self, active: bool):
        if self.property("selected") == active:
            return
        self.setProperty("selected", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.usable:
            self.activated.emit(self.slot)
        super().mousePressEvent(e)


class Overlay(QDialog):
    picked = Signal(object)
    visibility_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._preserve_target_focus = False
        self.target_hwnd = 0
        self.page = "slots"
        self.tiles: list[SlotCard] = []
        self.index = 0
        self.columns = 3
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        self.panel = QFrame()
        self.panel.setObjectName("hud")
        outer.addWidget(self.panel)
        body = QVBoxLayout(self.panel)
        body.setContentsMargins(26, 24, 26, 20)
        body.setSpacing(15)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(5)
        self.heading = label(tr("입력기 선택"), "overlayTitle")
        titles.addWidget(self.heading)
        self.subtitle = label(tr("1–9, 0, A–E 또는 방향키로 선택"), "overlaySub")
        self.subtitle.setWordWrap(True)
        titles.addWidget(self.subtitle)
        head.addLayout(titles, 1)
        self.shortcut_hint = label("CapsLock + Q", "hintKey")
        self.shortcut_hint.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        head.addWidget(self.shortcut_hint)
        body.addLayout(head)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid_scroll.setWidget(self.grid_host)
        body.addWidget(self.grid_scroll, 1)
        self._tile_signature = None
        self.footer_hint = label(tr("Enter 선택    ·    Esc 닫기"), "small")
        body.addWidget(self.footer_hint)
        self.slots: list[dict[str, str]] = []
        self._width_slot: dict[str, str] | None = None
        self._selection_revision = 0
        self.resize(650, 440)

    def retranslate(self):
        """Apply a new display language to an existing overlay instantly."""
        self.heading.setText(tr('가타카나 문자 폭') if self.page == 'width' else tr('입력기 선택'))
        self.subtitle.setText(tr('전각 또는 반각을 선택하세요') if self.page == 'width'
                              else tr('1–9, 0, A–E 또는 방향키로 선택'))
        self.footer_hint.setText(tr('Enter 선택    ·    Esc 닫기'))
        if self.isVisible():
            slots = [dict(tile.slot) for tile in self.tiles]
            self.rebuild(slots, self.page == 'width')
            self._recenter()

    def set_shortcut(self, binding: HotkeyBinding):
        self.shortcut_hint.setText(binding.title)

    def rebuild(self, slots: list[dict[str, str]], width_prompt: bool = False):
        self.page = "width" if width_prompt else "slots"
        self.index = 0
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        self.columns = min(5 if len(slots) > 6 and available and available.width() >= 1100 else 3,
                           max(1, len(slots)))
        self.heading.setText(tr("가타카나 문자 폭") if width_prompt else tr("입력기 선택"))
        self.subtitle.setText(tr("전각 또는 반각을 선택하세요") if width_prompt else tr("1–9, 0, A–E 또는 방향키로 선택"))
        layouts = {x.hkl: x for x in available_layouts()}
        signature = (tuple(tuple(sorted(slot.items())) for slot in slots), tuple(layouts.items()),
                     width_prompt, language(), self.columns)
        if signature != self._tile_signature:
            clear_layout(self.grid)
            self.tiles.clear()
            for i, slot in enumerate(slots):
                tile = SlotCard(slot, layouts.get(slot["hkl"]), i+1)
                tile.activated.connect(self._activate)
                self.tiles.append(tile)
                self.grid.addWidget(tile, i // self.columns, i % self.columns)
            self._tile_signature = signature
        self._highlight(0)
        rows = (len(slots) + self.columns - 1) // self.columns
        self.grid_host.setMinimumHeight(max(0, rows * 130 - 12))
        width = 1075 if self.columns == 5 else 665 if self.columns >= 3 else 520
        height = 173 + rows * 130
        self.setFixedSize(min(width, available.width()-24) if available else width,
                          min(height, available.height()-24) if available else height)

    def _highlight(self, i: int):
        if not self.tiles:
            return
        i %= len(self.tiles)
        if not self.tiles[i].usable:
            valid = next((n for n, tile in enumerate(self.tiles) if tile.usable), None)
            if valid is None:
                return
            i = valid
        self.index = i
        for n, tile in enumerate(self.tiles):
            tile.selected(n == i)
        self.grid_scroll.ensureWidgetVisible(self.tiles[i], 0, 8)

    def _activate(self, slot: dict[str, str]):
        if self.page == "slots" and slot["mode"] == "ja_katakana_ask":
            self._width_slot = dict(slot)
            self.rebuild([
                {**slot, "mode":"ja_katakana_full", "name":tr("전각 가타카나")},
                {**slot, "mode":"ja_katakana_half", "name":tr("반각 가타카나")},
            ], width_prompt=True)
            self._recenter()
            return
        self.hide()
        # Let Windows restore focus before sending IME commands to the target.
        revision = self._selection_revision
        QTimer.singleShot(40, lambda selected=dict(slot), rev=revision:
                          self.picked.emit(selected) if rev == self._selection_revision else None)

    def set_preserve_target_focus(self, enabled: bool):
        """Use the navigation hook without deactivating Explorer's text editor.

        Explorer can end/recreate an address, search or rename editor on
        deactivation. Keep that input context alive rather than weakening the
        exact-target checks used before IME commands and synthetic keys.
        If the hook cannot start, retain Qt's focused keyboard fallback.
        """
        self._preserve_target_focus = enabled
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, enabled)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, enabled)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus if enabled else Qt.FocusPolicy.StrongFocus)

    def open(self, slots: list[dict[str, str]], hwnd: int):
        self._selection_revision += 1
        self.target_hwnd = hwnd
        self.slots = [dict(s) for s in slots]
        self._width_slot = None
        self.rebuild(self.slots)
        self._recenter()
        self.show()
        self.raise_()
        if not self._preserve_target_focus:
            self.activateWindow()
            self.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibility_changed.emit(False)

    def navigate_virtual_key(self, vk: int) -> None:
        """Navigate even if the focus remains in another Windows application."""
        mapping = {
            0x25: Qt.Key.Key_Left, 0x26: Qt.Key.Key_Up,
            0x27: Qt.Key.Key_Right, 0x28: Qt.Key.Key_Down,
            0x0D: Qt.Key.Key_Return, 0x1B: Qt.Key.Key_Escape,
            0x20: Qt.Key.Key_Space,
        }
        if 0x30 <= vk <= 0x39:
            key = Qt.Key(vk)
        elif 0x60 <= vk <= 0x69:
            key = Qt.Key(int(Qt.Key.Key_0) + vk - 0x60)
        elif 0x41 <= vk <= 0x45:
            key = Qt.Key(vk)
        else:
            key = mapping.get(vk)
        if key is not None and self.isVisible():
            self._handle_key(key)

    def _recenter(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.move(rect.center().x() - self.width() // 2, rect.center().y() - self.height() // 2)

    def _handle_key(self, key):
        if key == Qt.Key.Key_Escape:
            if self.page == "width":
                self.rebuild(self.slots)
                self._recenter()
            else:
                self.hide()
                if self.target_hwnd:
                    foreground_target(self.target_hwnd)
            return True
        if not self.tiles:
            return True
        character = chr(int(key)) if 0 <= int(key) < 128 else ''
        if character in SELECTION_KEYS and character:
            n = SELECTION_KEYS.index(character)
            if n < len(self.tiles) and self.tiles[n].usable:
                self._activate(self.tiles[n].slot)
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._activate(self.tiles[self.index].slot)
            return True
        directions = {Qt.Key.Key_Left:"left", Qt.Key.Key_Right:"right",
                      Qt.Key.Key_Up:"up", Qt.Key.Key_Down:"down"}
        if key in directions:
            direction = directions[key]
            candidate = move_selection(self.index, len(self.tiles), self.columns, direction)
            if candidate != self.index and not self.tiles[candidate].usable:
                # Skip unavailable layouts without jumping to slot 1.
                seen = {self.index, candidate}
                while not self.tiles[candidate].usable:
                    next_candidate = move_selection(candidate, len(self.tiles), self.columns, direction)
                    if next_candidate in seen:
                        candidate = self.index
                        break
                    candidate = next_candidate
                    seen.add(candidate)
            if self.tiles[candidate].usable:
                self._highlight(candidate)
            return True
        return False


    def keyPressEvent(self, e):
        if not self._handle_key(e.key()):
            super().keyPressEvent(e)

class SlotComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            # Wheel input over a closed field belongs to the surrounding list.
            parent = self.parentWidget()
            while parent is not None and not isinstance(parent, QScrollArea):
                parent = parent.parentWidget()
            if parent is not None:
                parent.wheelEvent(event)
                event.accept()
            else:
                event.ignore()


class SlotScrollArea(QScrollArea):
    def wheelEvent(self, event):
        pixels = event.pixelDelta()
        if pixels.y():
            bar = self.verticalScrollBar()
            bar.setValue(bar.value() - pixels.y())
            event.accept()
        else:
            super().wheelEvent(event)


class SlotEditor(QWidget):
    saved = Signal(object)

    def __init__(self, slots: list[dict[str, str]]):
        super().__init__()
        self.slots = [dict(s) for s in slots]
        self.layouts: list[LayoutInfo] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(15)
        head = QHBoxLayout()
        head.addWidget(label(tr("입력기 슬롯"), "section"))
        head.addStretch()
        self.count_label = label("", "small")
        head.addWidget(self.count_label)
        head.addWidget(button(tr("목록 새로고침"), self.refresh, "ghost"))
        root.addLayout(head)
        info = label(tr("Windows에서 사용할 수 있는 입력기"), "muted")
        root.addWidget(info)
        self.scroll = SlotScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().setSingleStep(12)
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.list_layout.setContentsMargins(0, 0, 8, 0)
        self.list_layout.setSpacing(9)
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)
        foot = QHBoxLayout()
        self.add = button(tr("+ 슬롯 추가"), self.add_slot, "ghost")
        foot.addWidget(self.add)
        foot.addStretch(1)
        foot.addWidget(button(tr("변경사항 저장"), self.save, "primary"))
        root.addLayout(foot)
        self.refresh()

    def set_slots(self, slots):
        self.slots = [dict(s) for s in slots]
        self.refresh()

    def refresh(self):
        self.layouts = available_layouts()
        # Keep unsaved edits and temporarily unavailable layouts visible.
        self.slots = editable_slots(self.slots, self.layouts)
        self.rebuild()

    def rebuild(self):
        self._list_revision = getattr(self, "_list_revision", 0) + 1
        clear_layout(self.list_layout)
        self._name_editors = []
        self.count_label.setText(f"{len(self.slots)} / {MAX_SLOTS}")
        self.add.setEnabled(bool(self.layouts) and len(self.slots) < MAX_SLOTS)
        for i, slot in enumerate(self.slots):
            frame = QFrame()
            frame.setObjectName("slotRow")
            stack = QVBoxLayout(frame)
            stack.setContentsMargins(15, 13, 15, 13)
            stack.setSpacing(9)
            top = QHBoxLayout()
            top.setSpacing(9)
            number = label(f"{i+1:02d}", "tileCode")
            number.setFixedWidth(32)
            top.addWidget(number)
            layout = SlotComboBox()
            layout.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            layout.setMinimumContentsLength(16)
            layout.view().setUniformItemSizes(True)
            layout.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout.setToolTip(tr("이 슬롯에서 사용할 Windows 입력기"))
            if slot["hkl"] not in {item.hkl for item in self.layouts}:
                layout.addItem(tr("사용할 수 없는 입력기 — 다시 선택"), slot["hkl"])
            for item in self.layouts:
                layout.addItem(item.display, item.hkl)
                item_font = layout.font()
                item_font.setFamily(text_font_family(item.display))
                layout.setItemData(layout.count()-1, item_font, Qt.ItemDataRole.FontRole)
            layout.setCurrentIndex(max(0, layout.findData(slot["hkl"])))
            apply_text_font(layout, layout.currentText())
            layout.currentIndexChanged.connect(lambda _, idx=i, w=layout: self._select_layout(idx, w.currentData()))
            top.addWidget(layout, 1)
            up = button("↑", lambda _, idx=i: self.move_slot(idx, -1), "ghost")
            up.setToolTip(tr("위로 이동"))
            up.setAccessibleName(tr("위로 이동"))
            up.setFixedWidth(37)
            up.setEnabled(i > 0)
            top.addWidget(up)
            down = button("↓", lambda _, idx=i: self.move_slot(idx, 1), "ghost")
            down.setToolTip(tr("아래로 이동"))
            down.setAccessibleName(tr("아래로 이동"))
            down.setFixedWidth(37)
            down.setEnabled(i < len(self.slots)-1)
            top.addWidget(down)
            stack.addLayout(top)
            bottom = QHBoxLayout()
            bottom.setSpacing(9)
            bottom.addSpacing(41)
            modes = SlotComboBox()
            modes.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            modes.setMinimumContentsLength(12)
            modes.view().setUniformItemSizes(True)
            modes.setMinimumWidth(125)
            info = next((x for x in self.layouts if x.hkl == slot["hkl"]), "standard")
            for mode_key, mode_name in mode_options(info):
                text = tr(mode_name)
                modes.addItem(text, mode_key)
                mode_font = modes.font()
                mode_font.setFamily(text_font_family(text))
                modes.setItemData(modes.count()-1, mode_font, Qt.ItemDataRole.FontRole)
            modes.setCurrentIndex(max(0, modes.findData(slot["mode"])))
            apply_text_font(modes, modes.currentText())
            def mode_changed(_, idx=i, w=modes):
                apply_text_font(w, w.currentText())
                self._select_mode(idx, w.currentData())
            modes.currentIndexChanged.connect(mode_changed)
            bottom.addWidget(modes, 1)
            name = QLineEdit(slot.get("name", ""))
            placeholder = tr("표시 이름") if not name.text() else ""
            apply_text_font(name, name.text() or placeholder)
            self._name_editors.append(name)
            name.setPlaceholderText(placeholder)
            name.setMaxLength(32)
            name.textEdited.connect(lambda value, idx=i: self._set_name(idx, value))
            bottom.addWidget(name, 1)
            remove = button(tr("삭제"), lambda _, idx=i: self.delete_slot(idx), "danger")
            remove.setEnabled(len(self.slots) > 1)
            bottom.addWidget(remove)
            stack.addLayout(bottom)
            self.list_layout.addWidget(frame)
        self.list_layout.addStretch(1)

    def _select_layout(self, i, hkl):
        if not 0 <= i < len(self.slots):
            return
        layout = next((x for x in self.layouts if x.hkl == hkl), None)
        if layout is None:
            return
        mode = preferred_mode(layout)
        self.slots[i] = {"hkl": layout.hkl, "mode": mode, "name": default_name(layout, mode)}
        QTimer.singleShot(0, self.rebuild)

    def _select_mode(self, i, mode):
        if mode is None or not 0 <= i < len(self.slots):
            return
        slot = self.slots[i]
        layout = next((x for x in self.layouts if x.hkl == slot["hkl"]), None)
        old_default = default_name(layout, slot["mode"]) if layout else ""
        if not slot["name"] or slot["name"] == old_default:
            slot["name"] = default_name(layout, mode) if layout else ""
        slot["mode"] = mode
        # A mode change only changes this name; keep the open row and its focus.
        self._name_editors[i].setText(slot["name"])
        placeholder = tr("표시 이름") if not slot["name"] else ""
        self._name_editors[i].setPlaceholderText(placeholder)
        apply_text_font(self._name_editors[i], slot["name"] or placeholder)

    def _set_name(self, i, name):
        if 0 <= i < len(self.slots):
            self.slots[i]["name"] = name[:32]
            editor = self._name_editors[i]
            placeholder = tr("표시 이름") if not name else ""
            editor.setPlaceholderText(placeholder)
            apply_text_font(editor, name or placeholder)

    def move_slot(self, i, move):
        j = i + move
        if not (0 <= i < len(self.slots) and 0 <= j < len(self.slots)):
            return
        self.slots[i], self.slots[j] = self.slots[j], self.slots[i]
        self.rebuild()

    def delete_slot(self, i):
        if len(self.slots) > 1 and 0 <= i < len(self.slots):
            self.slots.pop(i)
            self.rebuild()

    def add_slot(self):
        if len(self.slots) >= MAX_SLOTS or not self.layouts:
            return
        chosen = next((x for x in self.layouts if x.hkl not in {s["hkl"] for s in self.slots}), self.layouts[0])
        mode = preferred_mode(chosen)
        self.slots.append({"hkl":chosen.hkl, "mode":mode, "name":default_name(chosen, mode)})
        self.rebuild()
        revision, index = self._list_revision, len(self.slots) - 1
        # Scroll only after Qt has laid out the new row and updated the range.
        QTimer.singleShot(0, lambda: self._reveal_slot(index, revision))

    def _reveal_slot(self, index, revision):
        if revision != self._list_revision or not 0 <= index < len(self.slots):
            return
        item = self.list_layout.itemAt(index)
        if item is not None and item.widget() is not None:
            self.list_layout.activate()
            self.scroll.ensureWidgetVisible(item.widget(), 0, 12)

    def save(self):
        if not self.slots:
            QMessageBox.warning(self, tr("입력기 없음"), tr("입력기를 하나 이상 선택하세요."))
            return
        valid = {layout.hkl: layout for layout in available_layouts()}
        for slot in self.slots:
            layout = valid.get(slot["hkl"])
            if layout is None:
                QMessageBox.warning(self, tr("입력기 없음"), tr("사용할 수 없는 입력기가 있습니다. 다시 선택하거나 삭제하세요."))
                return
            if slot["mode"] not in {mode for mode, _ in mode_options(layout)}:
                QMessageBox.warning(self, tr("입력 모드 오류"), tr("설치된 입력기에 맞는 입력 모드를 선택하세요."))
                return
        self.saved.emit([dict(s) for s in self.slots])


class MainWindow(QWidget):
    open_overlay = Signal()
    quit_requested = Signal()
    tray_hide_requested = Signal()
    settings_changed = Signal()
    ime_shortcut_changed = Signal(object)
    ime_toggle_requested = Signal()
    chinese_shortcut_changed = Signal(object)
    chinese_toggle_requested = Signal()
    shortcut_changed = Signal(object)
    language_requested = Signal(str)
    update_requested = Signal()
    enabled_requested = Signal(bool)
    feature_requested = Signal(str,bool)
    dictionary_saved = Signal(list)

    def __init__(self, store: QSettings, slots: list[dict[str, str]], first_run: bool):
        super().__init__()
        self.store = store
        self.setObjectName("window")
        self.setWindowTitle(f"Lexift  ·  v{VERSION}")
        self.setWindowIcon(icon())
        self.resize(1020, 690)
        self.setMinimumSize(850, 560)
        self._current_page = 0
        self._first_run = first_run
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("side")
        sidebar.setFixedWidth(226)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(18, 23, 18, 20)
        nav.setSpacing(6)
        nav.addWidget(brand_mark())
        nav.addWidget(label(tr("Input switcher"), "logoCaption"))
        nav.addSpacing(26)
        self.nav_buttons: list[QPushButton] = []
        for text in (tr("대시보드"), tr("입력기 슬롯"), tr("일반 설정"), tr("프로그램 정보"),tr('사용자 사전')):
            ix = len(self.nav_buttons)
            item = button(text, lambda _=False, n=ix: self.navigate(n), "nav")
            item.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_buttons.append(item)
            nav.addWidget(item)
        nav.addStretch(1)
        nav.addWidget(label(tr("버전 {version}").format(version=VERSION), "small"))
        nav.addWidget(button(tr("종료"), lambda _=False: self.quit_requested.emit(), "ghost"))
        root.addWidget(sidebar)
        right = QWidget()
        body = QVBoxLayout(right)
        body.setContentsMargins(34, 30, 34, 30)
        body.setSpacing(20)
        self.pages = QStackedWidget()
        body.addWidget(self.pages)
        root.addWidget(right, 1)
        self.dashboard = self._make_dashboard()
        self.pages.addWidget(self.dashboard)
        self.slot_editor = SlotEditor(slots)
        self.pages.addWidget(self._wrap_page(tr("입력기 슬롯"), tr("최대 15개까지 등록할 수 있습니다."), self.slot_editor))
        self._ready_pages = {0, 1}
        self.pages.addWidget(QWidget())
        self.pages.addWidget(QWidget())
        self.pages.addWidget(QWidget())
        # A menu click only switches an existing page. These small, fixed-size
        # editors are built once; no registry/model/widget setup on first visit.
        for index in (2, 3, 4):
            self._ensure_page(index)
        self.navigate(1 if first_run else 0)
        self._prepared_pages = set()
        self._preferences_timer=QTimer(self)
        self._preferences_timer.setSingleShot(True)
        self._preferences_timer.timeout.connect(self._prepare_next_page)
        self._preferences_timer.start(0)

    def _wrap_page(self, title: str, subtitle: str, content: QWidget) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(20)
        v.addWidget(label(title, "pageTitle"))
        v.addWidget(label(subtitle, "subtitle",wrap=True))
        v.addSpacing(3)
        v.addWidget(content, 1)
        return page

    def _make_dashboard(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(17)
        v.addWidget(brand_mark(222,74))
        v.addWidget(label(tr("입력기 선택"), "subtitle"))
        v.addSpacing(3)
        hero = QFrame()
        hero.setObjectName("panel")
        h = QHBoxLayout(hero)
        h.setContentsMargins(24, 24, 24, 24)
        titles = QVBoxLayout()
        titles.setSpacing(9)
        titles.addWidget(label(tr("빠른 전환"), "section"))
        self.dashboard_shortcut = label(self.current_binding().title, "metric")
        titles.addWidget(self.dashboard_shortcut)
        self.status = label(tr("단축키 대기 중"), "muted")
        titles.addWidget(self.status)
        h.addLayout(titles, 1)
        self.enabled_button = QPushButton("ON")
        self.enabled_button.setObjectName("toggle")
        self.enabled_button.setCheckable(True)
        self.enabled_button.setChecked(True)
        self.enabled_button.toggled.connect(self.enabled_requested.emit)
        h.addWidget(self.enabled_button)
        self.selector_button = button(tr("입력기 선택"), lambda _=False: self.open_overlay.emit(), "primary")
        h.addWidget(self.selector_button)
        v.addWidget(hero)
        line = QHBoxLayout()
        line.addWidget(label(tr("등록된 입력기"), "section"))
        line.addStretch(1)
        line.addWidget(button(tr("편집"), lambda: self.navigate(1), "ghost"))
        v.addLayout(line)
        self.preview_host = QWidget()
        self.preview = QGridLayout(self.preview_host)
        self.preview.setContentsMargins(0, 0, 0, 0)
        self.preview.setSpacing(11)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.preview_host)
        v.addWidget(preview_scroll, 1)
        return page

    def refresh_dashboard(self, slots):
        clear_layout(self.preview)
        self.status.setText(tr_count(len(slots), self.current_binding().title))
        layouts = {x.hkl: x for x in available_layouts()}
        for i, slot in enumerate(slots):
            card = QFrame()
            card.setObjectName("panel")
            block = QVBoxLayout(card)
            block.setContentsMargins(17, 17, 17, 17)
            block.setSpacing(7)
            item = layouts.get(slot["hkl"])
            block.addWidget(label(short_code(slot, item), "tileCode"))
            block.addWidget(label(slot.get("name") or (item.name if item else tr("입력기 없음")), "section"))
            block.addWidget(label(mode_label(item, slot["mode"]), "small"))
            self.preview.addWidget(card, i//3, i%3)

    def set_runtime_enabled(self, enabled):
        self.enabled_button.blockSignals(True)
        self.enabled_button.setChecked(enabled)
        self.enabled_button.setText("ON" if enabled else "OFF")
        self.enabled_button.blockSignals(False)
        self.selector_button.setEnabled(enabled)
        if not enabled:
            self.status.setText(tr("Lexift 비활성화"))
        else:
            self.status.setText(tr_count(len(self.slot_editor.slots), self.current_binding().title))

    def _make_preferences(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(19)
        v.addWidget(label(tr("일반 설정"), "pageTitle"))
        v.addWidget(label(tr("시작 옵션과 단축키"), "subtitle"))
        v.addWidget(label(tr('다른 프로그램의 입력창에서 한글 발음을 일본어·중국어 후보로 변환합니다.'), 'muted',wrap=True))
        panel = QFrame()
        panel.setObjectName("panel")
        content = QVBoxLayout(panel)
        content.setContentsMargins(23, 22, 23, 22)
        content.setSpacing(19)
        content.addWidget(label(tr("실행"), "section"))
        self.show_at_start = QCheckBox(tr("실행할 때 메인 창 표시"))
        apply_text_font(self.show_at_start, self.show_at_start.text())
        self.show_at_start.setChecked(self.store.value("general/show_dashboard", True, type=bool))
        self.show_at_start.toggled.connect(self._save_preferences)
        content.addWidget(self.show_at_start)
        self.start_notice = QCheckBox(tr("시작 알림 표시"))
        apply_text_font(self.start_notice, self.start_notice.text())
        self.start_notice.setChecked(self.store.value("general/start_notice", True, type=bool))
        self.start_notice.toggled.connect(self._save_preferences)
        content.addWidget(self.start_notice)
        self.sound_notice=QCheckBox(tr('알림음 재생'))
        self.sound_notice.setChecked(self.store.value('general/sound',True,type=bool))
        self.sound_notice.toggled.connect(lambda value:self.store.setValue('general/sound',value))
        content.addWidget(self.sound_notice)
        self.auto_start = QCheckBox(tr("Windows 로그인 시 자동 실행"))
        apply_text_font(self.auto_start, self.auto_start.text())
        self.auto_start.setChecked(startup_enabled())
        self.auto_start.toggled.connect(self._toggle_startup)
        content.addWidget(self.auto_start)
        v.addWidget(panel)
        panel2 = QFrame()
        panel2.setObjectName("panel")
        vv = QVBoxLayout(panel2)
        vv.setContentsMargins(23, 22, 23, 22)
        vv.setSpacing(10)
        vv.addWidget(label(tr('언어 스위칭'), "section"))
        self.feature_checks={}
        vv.addWidget(label(tr('입력기 선택'),'section'))
        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(10)
        shortcut_row.addWidget(self._feature_check('selector'))
        self.shortcut_modifier = QComboBox()
        for mode in MODES:
            self.shortcut_modifier.addItem(tr(MODE_LABELS[mode]), mode)
        self.shortcut_key = QComboBox()
        for key in KEY_LABELS:
            self.shortcut_key.addItem(key, key)
        shortcut_row.addWidget(self.shortcut_modifier, 2)
        shortcut_row.addWidget(self.shortcut_key, 1)
        self.selector_apply = button(tr("적용"), self._apply_shortcut, "primary")
        shortcut_row.addWidget(self.selector_apply)
        vv.addLayout(shortcut_row)
        v.addWidget(panel2)
        conversion_panel=QFrame();conversion_panel.setObjectName('panel')
        vv=QVBoxLayout(conversion_panel);vv.setContentsMargins(23,22,23,22);vv.setSpacing(10)
        vv.addWidget(label(tr('한글 환경 언어 변환'),'section'))
        if language() in ('en','ja'):
            vv.addWidget(label(tr('한국어 발음 입력용 기능입니다. 환경에 따라 지원하지 않을 수 있습니다. 한국어 IME의 한글 모드에서 사용하세요.'),'muted',wrap=True))
        vv.addWidget(label(tr('한–일 변환'), 'section'))
        ime_row = QHBoxLayout()
        ime_row.addWidget(self._feature_check('ja'))
        self.ime_modifier = QComboBox()
        for mode in MODES:
            self.ime_modifier.addItem(tr(MODE_LABELS[mode]), mode)
        self.ime_key = QComboBox()
        for key in KEY_LABELS:
            self.ime_key.addItem(key, key)
        ime_row.addWidget(self.ime_modifier, 2)
        ime_row.addWidget(self.ime_key, 1)
        self.ime_apply = button(tr('적용'), self._apply_ime_shortcut, 'primary')
        ime_row.addWidget(self.ime_apply)
        vv.addLayout(ime_row)
        vv.addWidget(label(tr('한–중 변환'), 'section'))
        chinese_row = QHBoxLayout()
        chinese_row.addWidget(self._feature_check('zh'))
        self.chinese_modifier = QComboBox()
        for mode in MODES:
            self.chinese_modifier.addItem(tr(MODE_LABELS[mode]), mode)
        self.chinese_key = QComboBox()
        for key in KEY_LABELS:
            self.chinese_key.addItem(key, key)
        chinese_row.addWidget(self.chinese_modifier, 2)
        chinese_row.addWidget(self.chinese_key, 1)
        self.chinese_apply = button(tr('적용'), self._apply_chinese_shortcut, 'primary')
        chinese_row.addWidget(self.chinese_apply)
        vv.addLayout(chinese_row)
        vv.addWidget(label(tr('한국어 IME의 한글 상태에서만 한–일·한–중 변환을 켤 수 있습니다.'), 'muted',wrap=True))
        self.shortcut_conflict = label('', 'hint')
        vv.addWidget(self.shortcut_conflict)
        for combo in (self.shortcut_modifier, self.shortcut_key, self.ime_modifier, self.ime_key, self.chinese_modifier, self.chinese_key):
            combo.currentIndexChanged.connect(self._validate_shortcuts)
        self.update_shortcut_ui(self.current_binding())
        self.update_ime_shortcut_ui(self.current_ime_binding())
        self.update_chinese_shortcut_ui(self.current_chinese_binding())
        v.addWidget(conversion_panel)
        language_panel = QFrame()
        language_panel.setObjectName("panel")
        lang_layout = QVBoxLayout(language_panel)
        lang_layout.setContentsMargins(23, 20, 23, 20)
        lang_layout.setSpacing(10)
        lang_layout.addWidget(label(tr("표시 언어"), "section"))
        self.language_combo = QComboBox()
        family = {"ja": "Yu Gothic UI", "zh_CN": "Microsoft YaHei UI",
                  "zh_TW": "Microsoft JhengHei UI"}.get(language())
        if family:
            self.language_combo.setStyleSheet(f'QComboBox {{ font-family:"{family}"; }}')
        # Do not measure every translated name to size a closed dropdown.
        # Missing-script fallback can scan thousands of installed font faces.
        self.language_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.language_combo.setMinimumContentsLength(14)
        self.language_combo.view().setUniformItemSizes(True)
        for code, native_name in LANGUAGES:
            self.language_combo.addItem(native_name, code)
            family = {"ja": "Yu Gothic UI", "zh_CN": "Microsoft YaHei UI",
                      "zh_TW": "Microsoft JhengHei UI"}.get(code, "Malgun Gothic")
            native_font = self.language_combo.font()
            native_font.setFamily(family)
            self.language_combo.setItemData(
                self.language_combo.count() - 1, native_font, Qt.ItemDataRole.FontRole)
        self.language_combo.setCurrentIndex(self.language_combo.findData(language()))
        self.language_combo.currentIndexChanged.connect(self._request_language)
        lang_layout.addWidget(self.language_combo)
        v.addWidget(language_panel)
        v.addWidget(button(tr("업데이트 확인"), lambda: self.update_requested.emit(), "ghost"))
        v.addStretch(1)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def _feature_check(self,name):
        check=QCheckBox(tr('사용'))
        check.setChecked(self.store.value('features/'+name,True,type=bool))
        check.toggled.connect(lambda value,name=name:self.feature_requested.emit(name,value))
        self.feature_checks[name]=check
        return check

    def set_feature_states(self,states):
        if 2 in self._ready_pages:
            for name,value in states.items():
                check=self.feature_checks[name];check.blockSignals(True)
                check.setChecked(value);check.blockSignals(False)
        self.selector_button.setEnabled(self.enabled_button.isChecked() and states.get('selector',True))

    def _make_dictionary(self):
        from custom_dictionary import CustomDictionary
        from dictionary_ui import DictionaryEditor
        dictionary=CustomDictionary(self.store)
        self.dictionary_editor=DictionaryEditor(None if dictionary.load_error else dictionary.entries)
        self.dictionary_editor.saved.connect(self.dictionary_saved.emit)
        return self._wrap_page(tr('사용자 사전'),tr('원하는 이름이나 단어가 후보에 없을 때 등록하세요. 예: 스미네 → 澄音 (한–일).'),self.dictionary_editor)

    def current_ime_binding(self):
        try:
            return HotkeyBinding(self.store.value('ime_hotkey/mode', 'caps', str),
                                 self.store.value('ime_hotkey/key', 'A', str))
        except ValueError:
            return HotkeyBinding('caps', 'A')

    def current_chinese_binding(self):
        try:
            return HotkeyBinding(self.store.value('chinese_hotkey/mode', 'caps', str),
                                 self.store.value('chinese_hotkey/key', 'C', str))
        except ValueError:
            return HotkeyBinding('caps','C')

    def update_chinese_shortcut_ui(self, binding):
        if 2 in self._ready_pages:
            self.chinese_modifier.setCurrentIndex(self.chinese_modifier.findData(binding.mode))
            self.chinese_key.setCurrentIndex(self.chinese_key.findData(binding.key))
            self._validate_shortcuts()

    def _apply_chinese_shortcut(self):
        binding=HotkeyBinding(self.chinese_modifier.currentData(),self.chinese_key.currentData())
        if not self._validate_shortcuts() or binding in (self.current_binding(),self.current_ime_binding()):
            QMessageBox.warning(self,tr('단축키'),tr('이미 사용 중인 단축키입니다.'))
            return
        self.chinese_shortcut_changed.emit(binding)

    def _validate_shortcuts(self, *_):
        values=[(modifier.currentData(),key.currentData()) for modifier,key in
                ((self.shortcut_modifier,self.shortcut_key),(self.ime_modifier,self.ime_key),
                 (self.chinese_modifier,self.chinese_key))]
        conflict=len(set(values))!=len(values)
        self.shortcut_conflict.setText(tr('단축키가 겹칩니다. 서로 다른 조합을 선택하세요.') if conflict else '')
        for apply in (self.selector_apply,self.ime_apply,self.chinese_apply):
            apply.setEnabled(not conflict)
        return not conflict

    def _apply_ime_shortcut(self):
        binding = HotkeyBinding(self.ime_modifier.currentData(), self.ime_key.currentData())
        if not self._validate_shortcuts() or binding in (self.current_binding(), self.current_chinese_binding()):
            QMessageBox.warning(self, tr('단축키'), tr('다른 기능의 단축키와 겹쳐 저장할 수 없습니다.'))
            return
        self.ime_shortcut_changed.emit(binding)

    def update_ime_shortcut_ui(self, binding):
        if 2 in self._ready_pages:
            self.ime_modifier.setCurrentIndex(self.ime_modifier.findData(binding.mode))
            self.ime_key.setCurrentIndex(self.ime_key.findData(binding.key))
            self._validate_shortcuts()

    def _request_language(self, _index: int) -> None:
        code = self.language_combo.currentData()
        if code and code != language():
            self.language_requested.emit(code)

    def current_binding(self) -> HotkeyBinding:
        try:
            return HotkeyBinding(self.store.value("hotkey/mode", "caps", str),
                                 self.store.value("hotkey/key", "Q", str))
        except ValueError:
            return HotkeyBinding()

    def _apply_shortcut(self):
        try:
            binding = HotkeyBinding(self.shortcut_modifier.currentData(),
                                    self.shortcut_key.currentData())
        except ValueError as error:
            QMessageBox.warning(self, tr("단축키"), error_text(error, "shortcut"))
            return
        if not self._validate_shortcuts() or binding in (self.current_ime_binding(), self.current_chinese_binding()):
            QMessageBox.warning(self, tr('단축키'), '다른 기능의 단축키와 겹쳐 저장할 수 없습니다.')
            return
        # Ctrl+Alt is also used by AltGr on several European layouts.
        if binding.mode == "ctrl_alt":
            choice = QMessageBox.question(
                self, tr("단축키 확인"),
                tr("Ctrl + Alt 조합은 일부 키보드에서 AltGr 입력과 겹칠 수 있습니다. 적용할까요?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if choice != QMessageBox.StandardButton.Yes:
                self.update_shortcut_ui(self.current_binding())
                return
        self.shortcut_changed.emit(binding)

    def update_shortcut_ui(self, binding: HotkeyBinding):
        if 2 in self._ready_pages:
            self.shortcut_modifier.setCurrentIndex(self.shortcut_modifier.findData(binding.mode))
            self.shortcut_key.setCurrentIndex(self.shortcut_key.findData(binding.key))
        self.dashboard_shortcut.setText(binding.title)
        self.status.setText(tr_count(len(self.slot_editor.slots), binding.title))

    def _toggle_startup(self, enabled: bool):
        try:
            set_startup_enabled(enabled)
        except OSError as error:
            self.auto_start.blockSignals(True)
            self.auto_start.setChecked(not enabled)
            self.auto_start.blockSignals(False)
            QMessageBox.warning(self, tr("자동 실행 설정"), tr('Windows 자동 실행 설정을 변경하지 못했습니다.'))

    def _save_preferences(self, *_):
        self.store.setValue("general/show_dashboard", self.show_at_start.isChecked())
        self.store.setValue("general/start_notice", self.start_notice.isChecked())
        self.store.sync()
        self.settings_changed.emit()

    def _make_about(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(18)
        v.addWidget(label(tr("프로그램 정보"), "pageTitle"))
        panel = QFrame()
        panel.setObjectName("panel")
        p = QVBoxLayout(panel)
        p.setContentsMargins(26, 25, 26, 25)
        p.setSpacing(14)
        p.addWidget(brand_mark(240,80))
        p.addWidget(label(tr("버전 {version}").format(version=VERSION) + "  ·  Windows 10/11", "muted"))
        p.addSpacing(8)
        p.addWidget(label(tr("개발: {name}").format(name="Lutté Laurent"), "section"))
        p.addWidget(label(tr("저작권 © {year} {name}").format(year=2026, name="Lutté Laurent"), "muted"))
        p.addSpacing(10)
        p.addWidget(label(tr("MIT 라이선스"), "section"))
        p.addWidget(label(tr("이 프로그램은 MIT 라이선스로 배포됩니다."), "muted"))
        p.addWidget(button(tr("오류 로그 열기"), self._open_log, "ghost"))
        p.addWidget(button(tr("업데이트 확인"), lambda: self.update_requested.emit(), "ghost"))
        v.addWidget(panel)
        special_panel = QFrame()
        special_panel.setObjectName("panel")
        special_layout = QVBoxLayout(special_panel)
        special_layout.setContentsMargins(26, 22, 26, 22)
        special_layout.setSpacing(12)
        special_layout.addWidget(label(tr("감사한 분들"), "section"))
        self.special_host = QWidget()
        self.special_list = QVBoxLayout(self.special_host)
        self.special_list.setContentsMargins(0, 0, 0, 0)
        self.special_list.setSpacing(9)
        special_layout.addWidget(self.special_host)
        v.addWidget(special_panel)
        self._reload_special_thanks()
        links_panel = QFrame()
        links_panel.setObjectName("panel")
        links = QVBoxLayout(links_panel)
        links.setContentsMargins(26, 18, 26, 18)
        links.setSpacing(10)
        for title, logo, address in (
            (tr("개발자 커피 사주기"), "paypal", "https://www.paypal.com/ncp/payment/XKVWYK7U2EAB4"),
            (tr("Github.io"), "github", "https://luttechan.github.io/index.html"),
        ):
            link = button(title, lambda checked=False, url=address: QDesktopServices.openUrl(QUrl(url)), "ghost")
            link.setIcon(QIcon(str(Path(__file__).resolve().parent / "Style" / f"{logo}.svg")))
            link.setIconSize(QSize(22, 22))
            link.setCursor(Qt.CursorShape.PointingHandCursor)
            link.setToolTip(address)
            link.setAccessibleName(title)
            link.setStyleSheet("text-align:left; padding:12px 16px;")
            links.addWidget(link)
        v.addWidget(links_panel)
        # Diagnostics have no imports, worker or sampling on the startup path.
        from runtime_stats import RuntimeStatsPanel
        self.runtime_stats = RuntimeStatsPanel()
        v.addWidget(self.runtime_stats)
        v.addStretch(1)
        # Preserve the v0.6 informational panels and styling.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.runtime_stats.watch_viewport(scroll)
        return scroll

    def _reload_special_thanks(self):
        clear_layout(self.special_list)
        items = get_special_thanks()
        if not items:
            self.special_list.addWidget(label("—", "muted"))
            return
        for language, names in items:
            row = QHBoxLayout()
            credit_language = {"Korean":"한국어", "English":"영어", "Japanese":"일본어",
                               "Russian":"러시아어", "French":"프랑스어", "Spanish":"스페인어",
                               "German":"독일어", "Chinese":"중국어"}.get(language, language)
            row.addWidget(label(tr(credit_language) + ' :', "muted"))
            row.addStretch(1)
            name = label(names, "section", wrap=True)
            if language == "Japanese":
                # This name includes Japanese glyphs absent from Malgun Gothic.
                # Select the Windows Japanese UI font without an all-font search.
                name.setStyleSheet('font-family:"Yu Gothic UI";')
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(name, 2)
            self.special_list.addLayout(row)

    def _open_log(self):
        location = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / PRODUCT / "lexift.log"
        if location.exists():
            os.startfile(str(location))
        else:
            QMessageBox.information(self, tr("오류 로그"), tr("아직 생성된 로그가 없습니다."))

    def _prepare_preferences(self):
        self._ensure_page(2)
        self._prepare_page_layout(2)

    def _prepare_page_layout(self, index):
        # Resolve style/word wrapping while idle. Render only the fixed viewport,
        # never the full (potentially long) scroll contents or every table row.
        # The temporary image is discarded, leaving Qt's reusable glyph cache.
        page = self.pages.widget(index)
        if page.isVisible():
            self._prepared_pages.add(index)
            return
        self.layout().activate()
        page.resize(self.pages.contentsRect().size())
        widgets = [page, *page.findChildren(QWidget)]
        for widget in widgets:
            widget.ensurePolished()
            if widget.layout() is not None:
                widget.layout().activate()
        if isinstance(page, QScrollArea) and page.widget() is not None:
            content = page.widget()
            content.resize(page.viewport().width(), content.sizeHint().height())
            content.layout().activate()
        if not page.size().isEmpty():
            size = QSize(min(page.width(),1280), min(page.height(),900))
            preview = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
            page.render(preview, QPoint(), QRegion(0,0,size.width(),size.height()))
        self._prepared_pages.add(index)

    def _prepare_next_page(self):
        for index in (2, 3, 4):
            if index not in self._prepared_pages:
                self._prepare_page_layout(index)
                if len(self._prepared_pages) < 3:
                    self._preferences_timer.start(0)
                return

    def _ensure_page(self, index):
        if index in (2, 3,4) and index not in self._ready_pages:
            page = {2:self._make_preferences,3:self._make_about,4:self._make_dictionary}[index]()
            placeholder = self.pages.widget(index)
            self.pages.removeWidget(placeholder)
            placeholder.deleteLater()
            self.pages.insertWidget(index, page)
            self._ready_pages.add(index)
            if index == 2:
                self.update_shortcut_ui(self.current_binding())
                self.update_ime_shortcut_ui(self.current_ime_binding())
                self.update_chinese_shortcut_ui(self.current_chinese_binding())


    def navigate(self, index: int):
        if index == self._current_page and self.nav_buttons[index].property("active") is True:
            return
        self._ensure_page(index)

        self._current_page = index
        self.pages.setCurrentIndex(index)
        for i, item in enumerate(self.nav_buttons):
            active = i == index
            if item.property("active") == active:
                continue
            item.setProperty("active", active)
            item.style().unpolish(item)
            item.style().polish(item)

    def closeEvent(self, event):
        # X closes only the main window; the input hook and tray stay active.
        # If the tray is unavailable, exit instead of leaving an invisible app.
        if QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray_hide_requested.emit()
        else:
            event.ignore()
            self.quit_requested.emit()


class Dispatcher(QObject):
    hooks_ready = Signal(str)
    hotkey = Signal(int)
    ime_requested = Signal(int)
    chinese_requested = Signal(int)
    navigation = Signal(int)


class QuitConfirmation(QDialog):
    """Reusable confirmation; open() keeps the Qt event loop running."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("window")
        self.setWindowTitle(tr("종료"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(360)
        area = QVBoxLayout(self)
        area.setContentsMargins(24, 24, 24, 20)
        area.setSpacing(22)
        area.addWidget(label(tr("정말로 종료하시겠습니까?")))
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_button = button(tr("취소"), self.reject, "ghost")
        self.cancel_button.setDefault(True)
        self.quit_button = button(tr("종료"), self.accept, "primary")
        self.quit_button.setAutoDefault(False)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.quit_button)
        area.addLayout(actions)
        self.ensurePolished()
        self.adjustSize()


class LexiftController(QObject):
    def __init__(self, qt: QApplication):
        super().__init__()
        self.qt = qt
        self.store = QSettings(ORGANIZATION, PRODUCT)
        from preferences import migrate_preferences
        migrate_preferences(self.store)
        self._job = 0
        self._last_hotkey = 0.0
        self._last_target = 0
        self._running = False
        self._hook_warming=False
        self._hook_notify=False
        self._enabled = True
        self.features={name:self.store.value('features/'+name,True,type=bool) for name in ('selector','ja','zh')}
        from custom_dictionary import CustomDictionary
        self.custom_dictionary=CustomDictionary(self.store)
        self._sounds=None
        self._stopping = False
        self._confirming_quit = False
        self._quit_dialog = None
        try:
            self.binding = HotkeyBinding(self.store.value("hotkey/mode", "caps", str),
                                         self.store.value("hotkey/key", "Q", str))
        except ValueError:
            self.binding = HotkeyBinding()
        try:
            self.ime_binding = HotkeyBinding(self.store.value('ime_hotkey/mode', 'caps', str),
                                             self.store.value('ime_hotkey/key', 'A', str))
        except ValueError:
            self.ime_binding = HotkeyBinding('caps', 'A')
        if self.ime_binding == self.binding:
            self.ime_binding = HotkeyBinding('caps', 'A' if self.binding.key != 'A' else 'J')
            self.store.setValue('ime_hotkey/mode', self.ime_binding.mode)
            self.store.setValue('ime_hotkey/key', self.ime_binding.key)
        try:
            self.chinese_binding=HotkeyBinding(self.store.value('chinese_hotkey/mode','caps',str),
                                               self.store.value('chinese_hotkey/key','C',str))
        except ValueError:
            self.chinese_binding=HotkeyBinding('caps','C')
        if self.chinese_binding in (self.binding,self.ime_binding):
            self.chinese_binding=next(HotkeyBinding('caps',key) for key in KEY_LABELS
                                      if HotkeyBinding('caps',key) not in (self.binding,self.ime_binding))
        self.store.setValue('chinese_hotkey/mode',self.chinese_binding.mode)
        self.store.setValue('chinese_hotkey/key',self.chinese_binding.key)
        self._last_ime_toggle = 0.0
        self._ime_toast = None
        layouts = available_layouts()
        raw = self.store.value("profiles/slots_json", "", str)
        try:
            saved = sanitized_slots(json.loads(raw)) if raw else []
        except (TypeError, ValueError):
            saved = []
        self.first_run = needs_first_run_setup(saved, layouts)
        self.slots = first_run_slots(layouts) if self.first_run else installed_slots(saved, layouts)
        if not self.slots:
            raise RuntimeError(tr("현재 Windows에서 사용할 수 있는 입력기가 없습니다."))
        self.overlay = Overlay()
        self.cursor_indicator = CursorIndicator()
        self.overlay.visibility_changed.connect(self._selector_visibility)
        self.overlay.picked.connect(self.apply_slot)
        self._window = None
        self.overlay.set_shortcut(self.binding)
        from notifications import NotificationTray
        from notification_sound import set_notifier
        set_notifier(self._sound)
        self.tray = NotificationTray(icon(), qt)
        self.tray.setToolTip(f"Lexift · {self.binding.title}")
        self.tray_menu = QMenu()
        self.toggle_action = self.tray_menu.addAction(tr("Lexift 작동 중"))
        self.toggle_action.setCheckable(True)
        self.toggle_action.setChecked(True)
        self.toggle_action.toggled.connect(self.set_enabled)
        self.tray_menu.addSeparator()
        self.tray_actions = [
            self.tray_menu.addAction(tr("입력기 선택"), self.show_overlay),
            self.tray_menu.addAction(tr("메인 창"), self.show_window),
        ]
        self.tray_menu.addSeparator()
        self.tray_actions.extend([
            self.tray_menu.addAction(tr("설정"), lambda: self.show_window(2)),
            self.tray_menu.addAction(tr("프로그램 정보"), lambda: self.show_window(3)),
        ])
        self.tray_menu.addSeparator()
        self.update_action = self.tray_menu.addAction(tr("업데이트 확인"), self.check_updates)
        self.tray_actions.append(self.tray_menu.addAction(tr("종료"), self.request_quit))
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_clicked)
        self.tray.messageClicked.connect(self.show_window)
        self.tray.show()
        self.dispatch = Dispatcher()
        self.dispatch.hooks_ready.connect(self._keyboard_ready)
        from korean_activation import KoreanInputActivator
        self._korean_activation=KoreanInputActivator(self)
        self._korean_activation.finished.connect(self._korean_activation_finished)
        self.dispatch.hotkey.connect(self._hotkey)
        self.dispatch.ime_requested.connect(self._show_ime_panel)
        self.dispatch.chinese_requested.connect(lambda hwnd:self._show_ime_panel(hwnd,'zh'))
        self.dispatch.navigation.connect(self._navigate_input)
        self.hook = self._make_keyboard_hook(self.binding)
        self.navigation_hook = OverlayNavigationHook(lambda key: self.dispatch.navigation.emit(key))
        self.overlay.visibility_changed.connect(self._navigation_visibility)
        from ime_inline import inline_mode
        inline_mode().dictionary=self.custom_dictionary
        inline_mode().visibility_changed.connect(self._navigation_visibility)
        inline_mode().failed.connect(self._conversion_failed)
        self._engine_prepare_timer=QTimer(self)
        self._engine_prepare_timer.setSingleShot(True)
        self._engine_prepare_timer.timeout.connect(self._prepare_engines)
        self._engine_prepare_timer.start(500)
        self._navigation_started = False
        self.qt.aboutToQuit.connect(self._shutdown_keyboard)
        self.updater = UpdateManager(self, VERSION)
        self._update_timer_started = False

    @property
    def window(self):
        if self._window is None:
            self._create_window()
        return self._window

    @window.setter
    def window(self, value):
        self._window = value

    def _create_window(self):
        self._window = MainWindow(self.store, self.slots, self.first_run)
        self.window.slot_editor.saved.connect(self.save_slots)
        self.window.open_overlay.connect(self.show_overlay)
        self.window.quit_requested.connect(self.request_quit)
        self.window.tray_hide_requested.connect(self.notify_running_in_tray)
        self.window.shortcut_changed.connect(self.change_shortcut)
        self.window.ime_shortcut_changed.connect(self.change_ime_shortcut)
        self.window.ime_toggle_requested.connect(self._show_ime_panel)
        self.window.chinese_shortcut_changed.connect(self.change_chinese_shortcut)
        self.window.chinese_toggle_requested.connect(lambda:self._show_ime_panel(0,'zh'))
        self.window.language_requested.connect(self.change_language)
        self.window.update_requested.connect(self.check_updates)
        self.window.enabled_requested.connect(self.set_enabled)
        self.window.feature_requested.connect(self.set_feature_enabled)
        self.window.dictionary_saved.connect(self.save_dictionary)
        self.window.refresh_dashboard(self.slots)
        self.overlay.set_shortcut(self.binding)
        self.window.update_shortcut_ui(self.binding)
        self._sync_enabled_ui()
        self._prepare_quit_dialog()

    def _prepare_quit_dialog(self):
        self._quit_dialog = QuitConfirmation(self._window)
        self._quit_dialog.finished.connect(self._quit_decided)

    def _quit_decided(self, result):
        self._confirming_quit = False
        if result == QDialog.DialogCode.Accepted:
            self.stop()

    def _sync_enabled_ui(self):
        enabled = self._enabled
        self.toggle_action.blockSignals(True)
        self.toggle_action.setChecked(enabled)
        self.toggle_action.setText(tr("Lexift 작동 중") if enabled else tr("Lexift 비활성화"))
        self.toggle_action.blockSignals(False)
        self.tray_actions[0].setEnabled(enabled and self.features['selector'])
        self.tray.setToolTip(f"Lexift · {'ON' if enabled else 'OFF'} · {self.binding.title}")
        if self._window is not None:
            self._window.set_runtime_enabled(enabled)
            self._window.set_feature_states(self.features)

    def _sound(self):
        if not self.store.value('general/sound',True,type=bool):return
        if self._sounds is None:
            from notification_sound import NotificationSound
            self._sounds=NotificationSound()
        self._sounds.play()

    def _conversion_failed(self,message):
        translated=tr(message)
        if translated==message and language()!='ko':
            translated=tr('발음 변환을 중단했습니다. 한글 입력 상태와 입력기 설치를 확인하세요.')
        self.tray.showMessage('Lexift · '+tr('발음 변환 OFF'),translated,QSystemTrayIcon.MessageIcon.Warning,4000)

    def _prepare_engines(self):
        if self._stopping or not self._enabled:return
        from ime_inline import inline_mode
        mode=inline_mode()
        for name in ('ja','zh'):
            if self.features[name] and name not in mode.engines:
                mode.prepare(name)
                self._engine_prepare_timer.start(150)
                return

    def set_feature_enabled(self,name,enabled):
        if name not in self.features or self._stopping:return
        enabled=bool(enabled)
        if self.features[name]==enabled:return
        previous=self.features[name];running=self._running
        if running:self.hook.stop();self._running=False
        self.features[name]=enabled
        replacement=self._make_keyboard_hook(self.binding)
        try:
            if self._enabled and not self.first_run and any(self.features.values()) and self._navigation_started:
                replacement.start()
        except Exception as error:
            replacement.stop();self.features[name]=previous
            self.hook=self._make_keyboard_hook(self.binding)
            try:
                if running:self.hook.start();self._running=True
            except Exception:logging.exception('Could not restore enabled features')
            self._sync_enabled_ui()
            QMessageBox.warning(self._window,tr('단축키 변경 실패'),error_text(error,'shortcut'));return
        self.hook=replacement
        self._running=self._enabled and not self.first_run and any(self.features.values()) and self._navigation_started
        if name=='selector' and not enabled:
            self._cancel_switch();self.overlay._selection_revision+=1;self.overlay.hide()
        if name in ('ja','zh') and not enabled:
            from ime_inline import inline_mode
            inline_mode().release(name)
        if not any(self.features.values()):
            self._shutdown_keyboard()
        elif self._enabled and not self.first_run and not self._navigation_started:
            self._running=False;self._start_hook(notify=False)
        if enabled and self._enabled:self._engine_prepare_timer.start(150)
        self.store.setValue('features/'+name,enabled);self.store.sync()
        self._sync_enabled_ui()

    def save_dictionary(self,entries):
        try:self.custom_dictionary.replace(entries)
        except (ValueError,OSError) as error:
            self.window.dictionary_editor.status.setText(tr(str(error)));return
        self.window.dictionary_editor.status.setText(tr('사전을 저장했습니다.'))
        from ime_inline import inline_mode
        mode=inline_mode()
        if mode.enabled:mode._search()

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if self._stopping or enabled == self._enabled:
            return
        self._enabled = enabled
        self._cancel_switch()
        self.overlay._selection_revision += 1
        self.overlay.hide()
        self._last_target = 0
        if enabled:
            if not self.first_run:
                self._start_hook(notify=False)
                if not self._running and not self._hook_warming:
                    self._enabled = False
                    keyboard_service().close()
                    self._navigation_started = False
        else:
            # Closing the owned connection removes both hooks in the worker.
            # Never wait for two acknowledgements on a menu/button click.
            self._shutdown_keyboard()
            from ime_inline import inline_mode
            inline_mode().close()
        self._sync_enabled_ui()
        text = (tr("Lexift 작동 중\n(단축키 : {shortcut})").format(shortcut=self.binding.title)
                if self._enabled else tr("Lexift 비활성화"))
        self.tray.showMessage("Lexift", text, QSystemTrayIcon.MessageIcon.Information, 2500)
        if self._enabled:self._engine_prepare_timer.start(150)

    def check_updates(self):
        self._cancel_switch()
        self.overlay._selection_revision += 1
        self.overlay.hide()
        self.updater.check()

    def change_language(self, code: str) -> None:
        """Recreate Qt widgets in-process; no restart or IME-hook interruption."""
        if code not in SUPPORTED or code == language():
            return
        previous = self.window
        page = previous._current_page
        was_visible = previous.isVisible()
        geometry = previous.geometry()
        edits = [dict(s) for s in previous.slot_editor.slots]
        dictionary_edits=([dict(row) for row in previous.dictionary_editor.model.rows]
                          if 4 in previous._ready_pages else None)
        # Preserve edits in progress when changing the display language.
        set_language(code)
        # Construct the editor with its unsaved edits once, rather than build
        # all rows from saved slots and immediately destroy/rebuild them.
        replacement = MainWindow(self.store, edits, self.first_run)
        replacement.slot_editor.saved.connect(self.save_slots)
        replacement.open_overlay.connect(self.show_overlay)
        replacement.quit_requested.connect(self.request_quit)
        replacement.tray_hide_requested.connect(self.notify_running_in_tray)
        replacement.shortcut_changed.connect(self.change_shortcut)
        replacement.ime_shortcut_changed.connect(self.change_ime_shortcut)
        replacement.ime_toggle_requested.connect(self._show_ime_panel)
        replacement.chinese_shortcut_changed.connect(self.change_chinese_shortcut)
        replacement.chinese_toggle_requested.connect(lambda:self._show_ime_panel(0,'zh'))
        replacement.language_requested.connect(self.change_language)
        replacement.update_requested.connect(self.check_updates)
        replacement.enabled_requested.connect(self.set_enabled)
        replacement.feature_requested.connect(self.set_feature_enabled)
        replacement.dictionary_saved.connect(self.save_dictionary)
        replacement.refresh_dashboard(self.slots)
        replacement.update_shortcut_ui(self.binding)
        replacement.setGeometry(geometry)
        replacement.navigate(page)
        if dictionary_edits is not None:
            replacement._ensure_page(4)
            model=replacement.dictionary_editor.model
            model.beginResetModel();model.rows=dictionary_edits;model.endResetModel()
        self.window = replacement
        self._prepare_quit_dialog()
        self.store.setValue('general/ui_language', code)
        self.store.sync()
        self.overlay.retranslate()
        for action, source in zip(self.tray_actions,
                ('입력기 선택','메인 창','설정','프로그램 정보','종료')):
            action.setText(tr(source))
        self.update_action.setText(tr("업데이트 확인"))
        self.updater.retranslate()
        self._sync_enabled_ui()
        previous.hide()
        if was_visible:
            replacement.show()
            replacement.raise_()
            replacement.activateWindow()
        previous.deleteLater()

    def start(self, *, show_main=False, background=False):
        if self.first_run:
            self.show_window(1)
            return
        show_dashboard = show_main or (not background and self.store.value("general/show_dashboard", True, type=bool))
        # Paint the complete main window before the worker's IPC handshake.
        if show_dashboard:
            self.show_window(0)
            self.qt.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        self._start_hook()
        # A manually launched app must never appear to be "not running".
        # Only --background (used for Windows auto-start) may stay in the tray.
        if not self._update_timer_started:
            self._update_timer_started = True
            QTimer.singleShot(8000, lambda: self.updater.check(automatic=True))

    def _start_hook(self, *, notify=True):
        if self._running or not getattr(self, "_enabled", True) or not any(getattr(self,'features',{'selector':True}).values()):
            return
        if self._warm_keyboard(notify):return
        if not self._navigation_started:
            try:
                self.navigation_hook.start()
                self._navigation_started = True
                self.overlay.set_preserve_target_focus(True)
            except Exception as error:
                self.overlay.set_preserve_target_focus(False)
                logging.exception("Overlay navigation hook failed")
                QMessageBox.warning(self.window, tr("오버레이 키보드"), tr('전역 방향키 연결에 실패했습니다.'))
        try:
            self.hook.start()
            self._running = True
            mark_ready(VERSION)
            if notify and self.store.value("general/start_notice", True, type=bool):
                QTimer.singleShot(100, self._notify_active)
        except Exception as error:
            self.window.status.setText(tr("단축키 연결 실패"))
            QMessageBox.warning(self.window, tr("단축키 오류"), error_text(error, "shortcut"))
            self.show_window(2)

    def _warm_keyboard(self,notify):
        worker=keyboard_service()
        if (worker.process is not None and worker.process.poll() is None and worker.connection
                and worker._bad_connection is not worker.connection):return False
        self._hook_notify=getattr(self,'_hook_notify',False) or notify
        if self._hook_warming:return True
        self._hook_warming=True
        import threading
        def prepare():
            error=''
            try:worker.ensure_started()
            except Exception as problem:error=str(problem)
            if self._stopping:
                worker.close(wait=False);return
            try:self.dispatch.hooks_ready.emit(error)
            except RuntimeError:worker.close(wait=False)
        self._hook_warm_thread=threading.Thread(target=prepare,daemon=True,name='Lexift-KeyboardStartup')
        self._hook_warm_thread.start();return True

    def _keyboard_ready(self,error):
        self._hook_warming=False
        notify=self._hook_notify;self._hook_notify=False
        if self._stopping or not self._enabled or not any(self.features.values()):
            keyboard_service().close(wait=False);return
        if error:
            self.tray.showMessage('Lexift',error_text(RuntimeError(error),'shortcut'),QSystemTrayIcon.MessageIcon.Warning,4000)
            return
        self._start_hook(notify=notify)

    def _notify_active(self):
        if self._running and self._enabled and not self._stopping:
            self.tray.showMessage("Lexift",
                tr("Lexift 작동 중\n(단축키 : {shortcut})").format(shortcut=self.binding.title),
                QSystemTrayIcon.MessageIcon.Information, 3500)

    def change_shortcut(self, binding: HotkeyBinding):
        if binding in (self.ime_binding,getattr(self,'chinese_binding',None)):
            self.window.update_shortcut_ui(self.binding)
            QMessageBox.warning(self.window, 'Lexift', '다른 기능의 단축키와 겹쳐 저장할 수 없습니다.')
            return
        if binding == self.binding:
            return
        old = self.binding
        running = self._running
        if running:
            self.hook.stop()
            self._running = False
        next_hook = self._make_keyboard_hook(binding)
        try:
            if running:
                next_hook.start()
        except Exception as error:
            self.hook = self._make_keyboard_hook(old)
            try:
                if running:
                    self.hook.start()
                    self._running = True
            except Exception:
                logging.exception("Failed to restore previous hotkey")
            self.window.update_shortcut_ui(old)
            QMessageBox.warning(self.window, tr("단축키 변경 실패"), error_text(error, "shortcut"))
            return
        self.binding = binding
        self.hook = next_hook
        self._running = running
        self.store.setValue("hotkey/mode", binding.mode)
        self.store.setValue("hotkey/key", binding.key)
        self.store.sync()
        self.overlay.set_shortcut(binding)
        self.window.update_shortcut_ui(binding)
        self._sync_enabled_ui()

    def change_ime_shortcut(self, binding):
        if binding in (self.binding,getattr(self,'chinese_binding',None)):
            self.window.update_ime_shortcut_ui(self.ime_binding)
            QMessageBox.warning(self.window, 'Lexift', '다른 기능의 단축키와 겹쳐 저장할 수 없습니다.')
            return
        if binding == self.ime_binding:
            return
        old = self.ime_binding
        running = self._running
        if running:
            self.hook.stop()
            self._running = False
        self.ime_binding = binding
        replacement = self._make_keyboard_hook(self.binding)
        try:
            if running:
                replacement.start()
        except Exception as error:
            replacement.stop()
            self.ime_binding = old
            self.hook = self._make_keyboard_hook(self.binding)
            try:
                if running:
                    self.hook.start()
                    self._running = True
            except Exception:
                logging.exception('Failed to restore keyboard shortcuts')
            self.window.update_ime_shortcut_ui(old)
            QMessageBox.warning(self.window, tr('단축키 변경 실패'), str(error))
            return
        self.hook = replacement
        self._running = running
        self.store.setValue('ime_hotkey/mode', binding.mode)
        self.store.setValue('ime_hotkey/key', binding.key)
        self.store.sync()
        self.window.update_ime_shortcut_ui(binding)

    def change_chinese_shortcut(self, binding):
        if binding in (self.binding,self.ime_binding):
            self.window.update_chinese_shortcut_ui(self.chinese_binding)
            QMessageBox.warning(self.window, 'Lexift', '다른 기능의 단축키와 겹쳐 저장할 수 없습니다.')
            return
        if binding == self.chinese_binding:
            return
        old = self.chinese_binding
        running = self._running
        if running:
            self.hook.stop()
            self._running = False
        self.chinese_binding = binding
        replacement = self._make_keyboard_hook(self.binding)
        try:
            if running:
                replacement.start()
        except Exception as error:
            replacement.stop()
            self.chinese_binding = old
            self.hook = self._make_keyboard_hook(self.binding)
            try:
                if running:
                    self.hook.start()
                    self._running = True
            except Exception:
                logging.exception('Failed to restore keyboard shortcuts')
            self.window.update_chinese_shortcut_ui(old)
            QMessageBox.warning(self.window, tr('단축키 변경 실패'), str(error))
            return
        self.hook = replacement
        self._running = running
        self.store.setValue('chinese_hotkey/mode', binding.mode)
        self.store.setValue('chinese_hotkey/key', binding.key)
        self.store.sync()
        self.window.update_chinese_shortcut_ui(binding)

    def save_slots(self, slots):
        slots = sanitized_slots(slots)
        if not slots:
            return
        self.slots = slots
        self.window._first_run = False
        self.store.setValue("profiles/slots_json", json.dumps(slots, ensure_ascii=False))
        self.store.sync()
        self.window.refresh_dashboard(slots)
        self._sync_enabled_ui()
        if self.first_run:
            self.first_run = False
            self._start_hook()
            self.show_window(0)
        else:
            self.tray.showMessage("Lexift", tr("입력기 설정을 저장했습니다."),
                                  QSystemTrayIcon.MessageIcon.Information, 2000)

    def show_window(self, page=0):
        self._cancel_switch()
        self.overlay._selection_revision += 1  # Cancel a not-yet-delivered pick.
        # Qt signals may pass a bool for clicked/activated callbacks.
        if not isinstance(page, int) or isinstance(page, bool):
            page = 0
        self.overlay.hide()
        self.window.navigate(page)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def show_overlay(self):
        if not getattr(self,'features',{}).get('selector',True):return
        if not getattr(self, "_enabled", True) or getattr(self, "_confirming_quit", False):
            return
        if self.first_run:
            self.show_window(1)
            return
        # Triggering from the app's own GUI must not target the app window.
        target = self._last_target
        if not target:
            QMessageBox.information(self.window, tr("입력기 전환"), tr_hint(self.binding.title))
            return
        if self._window is not None:
            self._window.hide()
        self.overlay.open(self.slots, target)

    def _make_keyboard_hook(self, binding):
        features=getattr(self,'features',{'selector':True,'ja':True,'zh':True})
        return CapsQHook((lambda hwnd:self.dispatch.hotkey.emit(hwnd or get_target_window())) if features['selector'] else None,binding,
                         on_ime=(lambda hwnd:self.dispatch.ime_requested.emit(hwnd)) if features['ja'] else None,ime_binding=self.ime_binding,
                         on_chinese=(lambda hwnd:self.dispatch.chinese_requested.emit(hwnd)) if features['zh'] else None,chinese_binding=self.chinese_binding)

    def _show_ime_panel(self, hwnd=0, language='ja'):
        if not getattr(self, '_enabled', True) or self._stopping or getattr(self, '_confirming_quit', False):
            return
        if not getattr(self,'features',{}).get(language,True):return
        from ime_inline import inline_mode
        mode=inline_mode()
        turning_off=mode.enabled and mode.language==language
        target=hwnd or get_target_window()
        # OFF must always remain available; enabling must never alter the IME.
        if not turning_off and (not target or not target_is_foreground(target)
                or current_language(target)!=LANG_KO or korean_is_hangul(target,timeout_ms=15) is not True):
            return
        now = time.monotonic()
        if now - self._last_ime_toggle < .28:
            return
        self._last_ime_toggle = now
        self._cancel_switch()
        self.overlay._selection_revision += 1
        self.overlay.hide()
        try:
            enabled = mode.toggle(language)
            self._korean_activation.cancel()
            if self._ime_toast is None:
                self._ime_toast = QLabel()
                self._ime_toast.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
                self._ime_toast.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                self._ime_toast.setStyleSheet('background:#182234;color:#ffffff;border-radius:12px;padding:14px 26px;font-size:16px;')
                self._ime_toast_timer = QTimer(self)
                self._ime_toast_timer.setSingleShot(True)
                self._ime_toast_timer.timeout.connect(self._ime_toast.hide)
            title=tr('한–중 변환' if language=='zh' else '한–일 변환')
            self._ime_toast.setText(title+('  ON' if enabled else '  OFF'))
            self._ime_toast.adjustSize()
            screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            area = screen.availableGeometry()
            self._ime_toast.move(area.center().x() - self._ime_toast.width() // 2, area.bottom() - 100)
            self._ime_toast.show()
            self._ime_toast_timer.start(1500)
            self._sound()
        except (OSError, RuntimeError) as error:
            QMessageBox.warning(self._window, 'Lexift', error_text(error))

    def _korean_activation_finished(self, ok):
        if not ok:
            from ime_inline import inline_mode
            if inline_mode().enabled:
                self.tray.showMessage('Lexift','한글 입력 전환을 확인하지 못했습니다. 대상 입력창의 한/영 상태를 확인해 주세요.',QSystemTrayIcon.MessageIcon.Warning,3000)

    def _hotkey(self, hwnd):
        if not getattr(self, "_enabled", True) or self._stopping or getattr(self, "_confirming_quit", False):
            return
        if not getattr(self,'features',{}).get('selector',True):return
        now = time.monotonic()
        if now - self._last_hotkey < .28:
            return
        self._last_hotkey = now
        if hwnd:
            self._last_target = hwnd
        if self.overlay.isVisible():
            self.overlay.hide()
        elif self._last_target:
            self.overlay.open(self.slots, self._last_target)

    def notify_running_in_tray(self):
        if self._stopping or not self.tray.isVisible():
            return
        self.tray.showMessage(
            "Lexift",
            (tr("Lexift 작동 중\n(단축키 : {shortcut})").format(shortcut=self.binding.title)
             if self._enabled else tr("Lexift 비활성화")),
            QSystemTrayIcon.MessageIcon.Information,
            3500,
        )

    def _tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window(0)

    def apply_slot(self, slot):
        if not getattr(self,'features',{}).get('selector',True):return
        if not getattr(self, "_enabled", True) or getattr(self, "_confirming_quit", False):
            return
        self.cursor_indicator.dismiss()
        self._job += 1
        job = self._job
        hwnd = self.overlay.target_hwnd
        try:
            target = hkl_number(slot["hkl"])
            if not foreground_target(hwnd):
                raise IMEError(tr("이전 입력 창으로 돌아갈 수 없습니다. 다시 단축키를 눌러주세요."))
            if hkl_string(current_hkl(hwnd)) == hkl_string(target):
                QTimer.singleShot(0, lambda: self._apply_mode(job, hwnd, slot))
                return
            request_hkl(hwnd, target)
        except (IMEError, ValueError) as error:
            self._error(str(error))
            return
        QTimer.singleShot(120, lambda: self._verify_layout(job, hwnd, slot, 0))

    def _verify_layout(self, job, hwnd, slot, count):
        if not self._switch_active(job, hwnd):
            return
        desired = hkl_number(slot["hkl"])
        if hkl_string(current_hkl(hwnd)) == hkl_string(desired):
            QTimer.singleShot(80, lambda: self._apply_mode(job, hwnd, slot))
            return
        if count == 2:
            try:
                request_hkl(hwnd, desired, to_root=True)
            except IMEError as error:
                self._error(str(error))
                return
        if count >= 5:
            self._cycle(job, hwnd, slot, 0)
            return
        QTimer.singleShot(130, lambda: self._verify_layout(job, hwnd, slot, count+1))

    def _cycle(self, job, hwnd, slot, n):
        if not self._switch_active(job, hwnd):
            return
        if hkl_string(current_hkl(hwnd)) == hkl_string(hkl_number(slot["hkl"])):
            self._apply_mode(job, hwnd, slot)
            return
        if n > len(available_layouts()):
            self._error(tr("입력기가 바뀌지 않았습니다. Windows 입력기 설정을 확인하세요."))
            return
        if not cycle_windows_language(hwnd):
            self._error(tr("Windows 입력기 전환 명령을 실행하지 못했습니다."))
            return
        QTimer.singleShot(220, lambda: self._cycle(job, hwnd, slot, n+1))

    def _apply_mode(self, job, hwnd, slot):
        if not self._switch_active(job, hwnd):
            return
        if hkl_string(current_hkl(hwnd)) != hkl_string(hkl_number(slot["hkl"])):
            self._error(tr("입력기가 바뀌지 않았습니다. Windows 입력기 설정을 확인하세요."))
            return
        mode = slot["mode"]
        if mode == "default":
            self._switch_succeeded(job, hwnd, slot)
            return
        if mode in ("ime_native", "ime_latin"):
            expected = mode == "ime_native"
            if ime_set_native(hwnd, expected):
                self._switch_succeeded(job, hwnd, slot)
            else:
                QTimer.singleShot(120, lambda: self._verify_ime_mode(job, hwnd, slot, expected, 0))
            return
        if mode in ("ko_hangul", "ko_latin"):
            expected = mode == "ko_hangul"
            if not korean_set(hwnd, expected):
                if not korean_toggle_key(hwnd):
                    self._error(tr("한/영 전환을 완료하지 못했습니다."))
                    return
                QTimer.singleShot(170, lambda: self._verify_korean(job, hwnd, slot, expected))
            else:
                self._switch_succeeded(job, hwnd, slot)
            return
        kind = {"ja_hiragana":"hiragana", "ja_katakana_full":"katakana_full",
                "ja_katakana_half":"katakana_half"}.get(mode)
        if kind:
            if not japanese_set(hwnd, kind):
                self._japanese_fallback(job, hwnd, slot, kind, 0)
            else:
                self._switch_succeeded(job, hwnd, slot)

    def _verify_ime_mode(self, job, hwnd, slot, expected, attempt):
        if not self._switch_active(job, hwnd):
            return
        if hkl_string(current_hkl(hwnd)) != hkl_string(hkl_number(slot["hkl"])):
            self._cancel_switch()
            return
        state = ime_native_status(hwnd)
        if state is expected:
            self._switch_succeeded(job, hwnd, slot)
            return
        if attempt >= 2:
            self._error(tr("IME 입력 모드를 확인하지 못했습니다. 입력기 설정을 확인하세요."))
            return
        if attempt == 0 and state is not None:
            ime_toggle_native(hwnd, expected)
        else:
            ime_set_native(hwnd, expected)
        QTimer.singleShot(120, lambda: self._verify_ime_mode(job, hwnd, slot, expected, attempt+1))

    def _verify_korean(self, job, hwnd, slot, expected):
        if not self._switch_active(job, hwnd):
            return
        if hkl_string(current_hkl(hwnd)) != hkl_string(hkl_number(slot["hkl"])):
            self._cancel_switch()
            return
        if korean_is_hangul(hwnd) != expected:
            self._error(tr("한국어 입력 상태를 확인하지 못했습니다."))
        else:
            self._switch_succeeded(job, hwnd, slot)

    def _japanese_fallback(self, job, hwnd, slot, kind, attempt):
        if not self._switch_active(job, hwnd):
            return
        if hkl_string(current_hkl(hwnd)) != hkl_string(hkl_number(slot["hkl"])):
            self._cancel_switch()
            return
        if japanese_matches(hwnd, kind):
            self._switch_succeeded(job, hwnd, slot)
            return
        if attempt >= (3 if kind == "katakana_half" else 1):
            self._error(tr("일본어 IME 모드를 확인하지 못했습니다."))
            return
        if not japanese_fallback_key(hwnd, kind):
            self._error(tr("일본어 IME 전환키를 전달하지 못했습니다."))
            return
        QTimer.singleShot(160, lambda: self._japanese_fallback(job, hwnd, slot, kind, attempt+1))

    def _cancel_switch(self):
        self._job += 1
        self.cursor_indicator.dismiss()

    def _selector_visibility(self, visible):
        from ime_inline import inline_mode
        inline_mode().set_paused(visible)
        if visible:
            self._cancel_switch()

    def _navigation_visibility(self, _visible=False):
        from ime_inline import inline_mode
        if self.overlay.isVisible():
            self.navigation_hook.set_active(1)
        elif inline_mode().pending_commit:
            self.navigation_hook.set_active(3,inline_mode().pending_commit.get('hwnd',0))
        elif inline_mode().visible():
            self.navigation_hook.set_active(2,inline_mode().snapshot.get('hwnd',0))
        else:
            self.navigation_hook.set_active(0)

    def _navigate_input(self, key):
        if self.overlay.isVisible():
            self.overlay.navigate_virtual_key(key)
        else:
            from ime_inline import inline_mode
            inline_mode().navigate(key)

    def _switch_active(self, job, hwnd):
        if job != self._job or self._stopping or not getattr(self, "_enabled", True):
            return False
        if self.overlay.isVisible() or not target_is_foreground(hwnd):
            self._cancel_switch()
            return False
        return True

    def _switch_succeeded(self, job, hwnd, slot):
        if not self._switch_active(job, hwnd):
            return
        if hkl_string(current_hkl(hwnd)) != hkl_string(hkl_number(slot["hkl"])):
            return
        layout = next((item for item in available_layouts() if item.hkl == slot["hkl"]), None)
        if layout is None:
            return
        # Use the verified mode rather than a potentially misleading custom name.
        detail = mode_label(layout, slot["mode"]) if slot["mode"] != "default" else layout.name
        self.cursor_indicator.show_language(f"{short_code(slot, layout)} · {detail}")
        self._job += 1  # Consume this completion exactly once.

    def _error(self, message):
        self._cancel_switch()
        logging.warning(message)
        message = error_text(Exception(message), "input")
        self.tray.showMessage("Lexift", message, QSystemTrayIcon.MessageIcon.Warning, 4500)

    def request_quit(self):
        if self._stopping or self._confirming_quit:
            return
        self._confirming_quit = True
        dialog = getattr(self, "_quit_dialog", None)
        if dialog is not None:
            # All widgets and translations already exist before the click.
            # Never enter MessageBoxW/exec() or wait for IPC in this path.
            self._job += 1
            self.overlay._selection_revision += 1
            dialog.cancel_button.setFocus()
            dialog.open()
            self.cursor_indicator.dismiss()
            self.overlay.hide()
            return
        try:
            self._cancel_switch()
            self.overlay._selection_revision += 1
            self.overlay.hide()
            window = self._window
            if sys.platform == "win32":
                # Avoid Qt dialog/font/style initialization on every exit path.
                owner = ctypes.c_void_p(int(window.winId())) if window is not None and window.isVisible() else None
                try:
                    confirmed = confirm_quit(owner)
                except NativeDialogUnavailable:
                    confirmed = QMessageBox.question(window, tr("종료"), tr("정말로 종료하시겠습니까?"),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
            else:
                confirmed = QMessageBox.question(
                    window if window is not None and window.isVisible() else None,
                    tr("종료"), tr("정말로 종료하시겠습니까?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                ) == QMessageBox.StandardButton.Yes
            if confirmed:
                self.stop()
        finally:
            self._confirming_quit = False

    def _shutdown_keyboard(self):
        if hasattr(self,'_engine_prepare_timer'):self._engine_prepare_timer.stop()
        if getattr(self,'_korean_activation',None):
            self._korean_activation.cancel()
        from ime_inline import inline_mode
        inline_mode().shutdown()
        worker = keyboard_service()
        worker.caps = None
        worker.navigation = None
        worker.close(wait=False)
        self.hook.thread = None
        self.navigation_hook.thread = None
        self._running = False
        self._navigation_started = False

    def stop(self):
        if self._stopping:
            return
        self._stopping = True
        if getattr(self,'_sounds',None):self._sounds.close()
        from ime_inline import inline_mode
        inline_mode().close()
        if hasattr(self, "updater"):
            self.updater.cancel()
        self.cursor_indicator.dismiss()
        self.overlay._selection_revision += 1
        self._job += 1  # Invalidate all delayed IME callbacks.
        self.overlay.hide()
        if self._window is not None:
            self._window.hide()
        self.tray.hide()
        self.tray.hide_notification()
        if getattr(self,'_ime_toast',None):self._ime_toast.hide()
        self._shutdown_keyboard()
        self.store.sync()
        self.qt.quit()


class LanguagePicker(QDialog):
    """First-launch language choice, independent of input slot setup."""
    def __init__(self, initial: str):
        super().__init__()
        self.setWindowTitle('Lexift')
        # Fallback only: the preferred first-run prompt is the native Windows dialog.
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setObjectName('window')
        self.setFixedWidth(410)
        area = QVBoxLayout(self)
        area.setContentsMargins(25, 23, 25, 23)
        area.setSpacing(15)
        self.picker_title = label(tr('언어를 선택하세요'), 'pageTitle')
        area.addWidget(self.picker_title)
        self.selector = QComboBox()
        for code, native in LANGUAGES:
            self.selector.addItem(native, code)
        self.selector.setCurrentIndex(max(0, self.selector.findData(initial)))
        area.addWidget(self.selector)
        self.picker_note = label(tr('나중에 설정에서 바꿀 수 있습니다.'), 'muted')
        area.addWidget(self.picker_note)
        self.start_button = button(tr('시작'), self.accept, 'primary')
        area.addWidget(self.start_button)
        self.selector.currentIndexChanged.connect(self._preview_language)

    def _preview_language(self, _index: int) -> None:
        code = self.selector.currentData()
        if code in SUPPORTED:
            set_language(code)
            self.picker_title.setText(tr('언어를 선택하세요'))
            self.picker_note.setText(tr('나중에 설정에서 바꿀 수 있습니다.'))
            self.start_button.setText(tr('시작'))

    def selected(self) -> str:
        return self.selector.currentData()

def setup_logging():
    path = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Lexift"
    path.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        handler = RotatingFileHandler(path / "lexift.log", maxBytes=1024*1024,
                                      backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        root.addHandler(handler)


def main() -> int:
    if sys.platform != "win32":
        print("Lexift is available on Windows 10/11 only.", file=sys.stderr)
        return 1
    setup_logging()
    load_saved_language()
    # Guard a second copy: two low-level keyboard hooks would conflict.
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    ctypes.set_last_error(0)
    mutex = kernel.CreateMutexW(None, False, "Local\\KanaShift-LutteLaurent")
    if not mutex:
        raise OSError(ctypes.get_last_error(), "Lexift mutex creation failed")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        logging.info("Second Lexift instance was not started")
        if "--show" in sys.argv or "--background" not in sys.argv:
            ctypes.windll.user32.MessageBoxW(
                None, tr("Lexift가 이미 실행 중입니다.\n작업표시줄 알림 영역의 K 아이콘을 확인하세요."),
                "Lexift", 0x40)
        kernel.CloseHandle(mutex)
        return 0
    show_main = "--show" in sys.argv
    background = "--background" in sys.argv
    qt_argv = [a for a in sys.argv if a not in ("--show", "--background")]
    qt = QApplication(qt_argv)
    qt.setApplicationName(PRODUCT)
    qt.setOrganizationName(ORGANIZATION)
    qt.setWindowIcon(icon())
    qt.setQuitOnLastWindowClosed(False)
    choose_font(qt)
    qt.setStyleSheet(QSS)
    prefs = QSettings(ORGANIZATION, PRODUCT)
    from preferences import migrate_preferences
    migrate_preferences(prefs)
    if startup_enabled():set_startup_enabled(True)
    preferred = prefs.value('general/ui_language', '', str)
    if preferred in SUPPORTED:
        set_language(preferred)
    def exception_handler(exc_type, value, traceback_obj):
        logging.error("Uncaught exception", exc_info=(exc_type, value, traceback_obj))
        sys.__excepthook__(exc_type, value, traceback_obj)
    sys.excepthook = exception_handler

    # First-run language choice MUST precede every loading/main/overlay window.
    # Native Windows radio-button TaskDialog stays in front on Windows 10/11.
    if preferred not in SUPPORTED:
        try:
            chosen = choose_ui_language(LANGUAGES, default='ko')
        except NativeDialogUnavailable:
            logging.exception("Native first-run language dialog unavailable; using Qt fallback")
            picker = LanguagePicker('ko')
            picker.show()
            picker.raise_()
            picker.activateWindow()
            if picker.exec() != QDialog.DialogCode.Accepted:
                kernel.CloseHandle(mutex)
                return 0
            chosen = picker.selected()
        if chosen is None:
            kernel.CloseHandle(mutex)
            return 0
        prefs.setValue('general/ui_language', chosen)
        prefs.sync()
        set_language(chosen)

    managers = {}

    def begin():
        try:
            managers["main"] = LexiftController(qt)
        except Exception as error:
            logging.exception("Startup failed")
            QMessageBox.critical(None, tr("Lexift 시작 오류"), error_text(error))
            qt.quit()
            return
        managers["main"].start(show_main=show_main, background=background)
        if managers["main"]._running or managers["main"].first_run or not any(managers['main'].features.values()):
            mark_ready(VERSION)

    # Build only the requested main window; background startup skips font layout.
    QTimer.singleShot(0, begin)
    result = qt.exec()
    if mutex:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(mutex)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
