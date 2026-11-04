"""Selector model only. React paints it; the existing native hook handles keys."""
from types import SimpleNamespace
from PySide6.QtCore import QObject, Signal, QTimer
from grid_navigation import move_selection
from layout_profiles import available_layouts
from i18n import language, tr

class DesktopSelector(QObject):
    picked = Signal(dict)
    visibility_changed = Signal(bool)
    keys = '1234567890ABCDE'

    def __init__(self, publish):
        super().__init__()
        self.publish = publish
        self._visible = False
        self._selection_revision = 0
        self.target_hwnd = 0
        self.index = 0
        self.columns = 3
        self.page = 'slots'
        self.slots = []
        self.tiles = []
        self.shortcut = 'Caps Lock + Q'
        self.watchdog = QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.setInterval(2000)
        self.watchdog.timeout.connect(self._unavailable)

    def frame(self):
        return dict(visible=self._visible, revision=self._selection_revision,
                    index=self.index, columns=self.columns, page=self.page,
                    language=language(), shortcut=self.shortcut,
                    items=[dict(slot=tile.slot, usable=tile.usable, key=self.keys[n])
                           for n,tile in enumerate(self.tiles)])

    def emit(self):
        self.publish('selector', self.frame())

    def prepare_slots(self, slots):
        self.slots = [dict(slot) for slot in slots]
        if not self._visible:self.rebuild(self.slots)

    def rebuild(self, slots, width_prompt=False):
        installed = {layout.hkl for layout in available_layouts()}
        self.tiles = [SimpleNamespace(slot=dict(slot), usable=slot['hkl'] in installed) for slot in slots]
        self.page = 'width' if width_prompt else 'slots'
        self.columns = min(3, max(1,len(slots)))
        self.index = next((n for n,tile in enumerate(self.tiles) if tile.usable),0)

    def open(self, slots, hwnd):
        self._selection_revision += 1
        self.target_hwnd = hwnd
        self.slots = [dict(slot) for slot in slots]
        self.rebuild(slots)
        self._visible = True
        self.visibility_changed.emit(True)
        self.emit()
        self.watchdog.start()

    def presented(self, revision):
        if revision == self._selection_revision and self._visible:self.watchdog.stop()

    def _unavailable(self):
        if not self._visible:return
        self.hide()
        self.publish('notice',dict(message=tr('선택 메뉴를 표시하지 못했습니다. 다시 시도하세요.'),kind='error'))

    def hide(self):
        self.watchdog.stop()
        if not self._visible:return
        self._visible = False
        self._selection_revision += 1
        self.emit()
        self.visibility_changed.emit(False)

    def isVisible(self):return self._visible
    def set_preserve_target_focus(self, enabled):pass
    def set_shortcut(self, binding):self.shortcut=binding.title
    def retranslate(self):
        if self._visible:self.emit()

    def select(self, index, revision):
        if not self._visible or revision != self._selection_revision:return
        if type(index) is not int or not 0 <= index < len(self.tiles):return
        tile=self.tiles[index]
        if not tile.usable:return
        slot=dict(tile.slot)
        if self.page=='slots' and slot['mode']=='ja_katakana_ask':
            self._selection_revision+=1
            self.rebuild([{**slot,'mode':'ja_katakana_full','name':tr('전각 가타카나')},
                          {**slot,'mode':'ja_katakana_half','name':tr('반각 가타카나')}],True)
            self.emit();self.watchdog.start();return
        self.hide()
        revision=self._selection_revision
        QTimer.singleShot(40,lambda:self.picked.emit(slot) if revision==self._selection_revision else None)

    def navigate_virtual_key(self, key):
        if not self._visible:return
        if key==0x1B:
            if self.page=='width':
                self._selection_revision+=1;self.rebuild(self.slots);self.emit();self.watchdog.start()
            else:self.hide()
            return
        if key in (0x0D,0x20):self.select(self.index,self._selection_revision);return
        if 0x60<=key<=0x69:key=key-0x60+0x30
        character=chr(key) if 0<=key<128 else ''
        if character and character in self.keys:
            self.select(self.keys.index(character),self._selection_revision);return
        direction={0x25:'left',0x26:'up',0x27:'right',0x28:'down'}.get(key)
        if direction and self.tiles:
            candidate=self.index
            for _ in self.tiles:
                candidate=move_selection(candidate,len(self.tiles),self.columns,direction)
                if self.tiles[candidate].usable:
                    self.index=candidate;break
            self.emit()
