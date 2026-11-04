"""A virtual table: no widget per dictionary row and no disk writes while typing."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, QEvent, Qt, Signal,QSize
from PySide6.QtGui import QFont,QFontMetrics
from PySide6.QtWidgets import (QAbstractItemView,QComboBox,QHBoxLayout,QHeaderView,
                              QLabel,QPushButton,QStyledItemDelegate,QTableView,QVBoxLayout,QWidget,QStyle,QStyleOptionButton)
from settings_controls import SettingsComboBox
from custom_dictionary import MAX_ENTRIES,validate
from i18n import tr,text_font_family

LANGUAGE_NAMES={'ja':'한–일 변환','zh':'한–중 변환','zh_tw':'한–중 번체','zh_bopomofo':'주음부호'}


class DictionaryRowHeader(QHeaderView):
    def __init__(self,parent):
        super().__init__(Qt.Orientation.Vertical,parent)
        self.setDefaultSectionSize(40)

    def sizeHint(self):
        # Row labels are always consecutive numbers. Measuring the largest
        # one once avoids Qt sampling hundreds of rows for the gutter width.
        return QSize(self.fontMetrics().horizontalAdvance(str(max(1,self.count())))+20,40)


class DictionaryModel(QAbstractTableModel):
    columns=('keyword','text','language')
    def __init__(self,entries,parent=None):
        super().__init__(parent);self.rows=[dict(e) for e in (entries or [])]
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return 0 if parent.isValid() else 4
    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole:
            return tr(('키워드','대치할 텍스트','언어','삭제')[section]) if orientation==Qt.Orientation.Horizontal else section+1
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        if index.column()==3:return tr('삭제') if role==Qt.ItemDataRole.DisplayRole else None
        value=self.rows[index.row()][self.columns[index.column()]]
        if role==Qt.ItemDataRole.EditRole:return value
        if role==Qt.ItemDataRole.DisplayRole:
            return tr(LANGUAGE_NAMES[value]) if index.column()==2 else value
        if role==Qt.ItemDataRole.FontRole and index.column()==1:
            return QFont(text_font_family(value))
    def flags(self,index):
        return super().flags(index) if index.column()==3 else super().flags(index)|Qt.ItemFlag.ItemIsEditable
    def setData(self,index,value,role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or index.column()>=3 or role!=Qt.ItemDataRole.EditRole:return False
        if index.column()==2 and value not in LANGUAGE_NAMES:return False
        self.rows[index.row()][self.columns[index.column()]]=str(value)
        self.dataChanged.emit(index,index,[role,Qt.ItemDataRole.DisplayRole]);return True
    def add(self):
        if len(self.rows)>=MAX_ENTRIES:return
        n=len(self.rows);self.beginInsertRows(QModelIndex(),n,n)
        self.rows.append(dict(keyword='',text='',language='ja'));self.endInsertRows()
    def remove(self,row):
        if 0<=row<len(self.rows):
            self.beginRemoveRows(QModelIndex(),row,row);self.rows.pop(row);self.endRemoveRows()


class LanguageDelegate(QStyledItemDelegate):
    def createEditor(self,parent,option,index):
        if index.column()!=2:return super().createEditor(parent,option,index)
        editor=SettingsComboBox(parent)
        for code,key in LANGUAGE_NAMES.items():editor.addItem(tr(key),code)
        return editor
    def setEditorData(self,editor,index):
        if index.column()!=2:return super().setEditorData(editor,index)
        editor.setCurrentIndex(editor.findData(index.data(Qt.ItemDataRole.EditRole)))
    def setModelData(self,editor,model,index):
        if index.column()!=2:return super().setModelData(editor,model,index)
        model.setData(index,editor.currentData())


class DeleteDelegate(QStyledItemDelegate):
    """Paint only visible buttons; a 1,000-entry dictionary needs no 1,000 widgets."""
    def __init__(self,parent=None):
        super().__init__(parent);self.pressed=QPersistentModelIndex()
    def paint(self,painter,option,index):
        button=QStyleOptionButton();button.rect=option.rect.adjusted(6,5,-6,-5)
        button.text=tr('삭제');button.state=QStyle.StateFlag.State_Enabled
        if self.pressed==index:button.state|=QStyle.StateFlag.State_Sunken
        option.widget.style().drawControl(QStyle.ControlElement.CE_PushButton,button,painter,option.widget)
    def editorEvent(self,event,model,option,index):
        if event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Space,Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Delete):
            model.remove(index.row());return True
        if event.type() not in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease):return False
        if event.button()!=Qt.MouseButton.LeftButton:return False
        inside=option.rect.adjusted(6,5,-6,-5).contains(event.position().toPoint())
        if event.type()==QEvent.Type.MouseButtonPress:
            self.pressed=QPersistentModelIndex(index) if inside else QPersistentModelIndex()
        else:
            clicked=inside and self.pressed==index
            self.pressed=QPersistentModelIndex()
            if clicked:model.remove(index.row())
        return True


class DictionaryEditor(QWidget):
    saved=Signal(list)
    def __init__(self,entries,parent=None):
        super().__init__(parent);layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.model=DictionaryModel(entries,self)
        # Resolve the first visible replacement's font while constructing the
        # settings window, rather than load its CJK face on the first click.
        if self.model.rows:
            family=text_font_family(self.model.rows[0]['text'])
            sample={'Malgun Gothic':'한','Yu Gothic UI':'日'}.get(family,'中')
            QFontMetrics(QFont(family)).horizontalAdvance(sample)
        self.table=QTableView();self.table.setModel(self.model)
        self.table.setVerticalHeader(DictionaryRowHeader(self.table))
        self.table.setStyleSheet('QTableView {background:#13151a;border:1px solid #2a2d35;gridline-color:#2a2d35;selection-background-color:#344356;} QHeaderView::section {background:#202329;color:#c9cbd1;border:0;padding:7px;} QTableCornerButton::section {background:#202329;border:0;}')
        self.table.setWordWrap(False)
        self.table.setItemDelegate(LanguageDelegate(self.table))
        self.table.setItemDelegateForColumn(3,DeleteDelegate(self.table))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header=self.table.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2,QHeaderView.ResizeMode.Fixed);header.resizeSection(2,170)
        header.setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed);header.resizeSection(3,82)
        layout.addWidget(self.table,1)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.status.setText(tr('저장된 사전을 읽지 못했습니다. 기존 데이터는 변경하지 않았습니다.') if entries is None else '')
        actions=QHBoxLayout();layout.addLayout(actions)
        add=QPushButton(tr('+ 항목 추가'));add.clicked.connect(self.add);actions.addWidget(add)
        self.add_button=add
        self.model.rowsInserted.connect(self._update_add_state)
        self.model.rowsRemoved.connect(self._update_add_state)
        self.model.modelReset.connect(self._update_add_state)
        self._update_add_state()
        actions.addStretch(1)
        save=QPushButton(tr('변경사항 저장'));save.setObjectName('primary');save.clicked.connect(self.save);actions.addWidget(save)
    def add(self):
        before=self.model.rowCount();self.model.add()
        if self.model.rowCount()==before:return
        index=self.model.index(self.model.rowCount()-1,0)
        self.table.setCurrentIndex(index);self.table.scrollTo(index);self.table.edit(index)
    def _update_add_state(self,*_):
        self.add_button.setEnabled(self.model.rowCount()<MAX_ENTRIES)
    def save(self):
        # Moving focus commits the delegate before validating its edited value.
        self.table.setFocus()
        try:rows=validate(self.model.rows)
        except ValueError as error:self.status.setText(tr(str(error)));return
        self.saved.emit(rows)
