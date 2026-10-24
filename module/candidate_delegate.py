"""Bounded font fallback for IME candidates, including emoji and rare kanji.

Qt's automatic fallback can scan the user's entire font collection for one
unsupported symbol. Select from explicit CJK/symbol fonts for each text run.
"""
from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QRawFont, QTextCharFormat, QTextLayout
from PySide6.QtWidgets import QApplication, QLabel, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class CandidateDelegate(QStyledItemDelegate):
    def __init__(self,parent=None,pixel_size=20):
        super().__init__(parent)
        self.fonts=[];self.raw=[];self.cache={}
        for family in ('Malgun Gothic','Yu Gothic UI','Meiryo','Microsoft YaHei UI',
                       'Segoe UI Emoji','Segoe UI Symbol','Segoe UI Historic'):
            font=QFont(family);font.setPixelSize(pixel_size)
            font.setStyleStrategy(QFont.StyleStrategy.NoFontMerging)
            self.fonts.append(font);self.raw.append(QRawFont.fromFont(font))

    def font_index(self,character):
        if character not in self.cache:
            if len(self.cache)>=4096:self.cache.clear()
            codepoint=ord(character)
            self.cache[character]=next((i for i,font in enumerate(self.raw)
                if font.isValid() and font.supportsCharacter(codepoint)),0)
        return self.cache[character]

    def formats(self,text):
        ranges=[];offset=0
        for character in text:
            font=self.fonts[self.font_index(character)]
            length=2 if ord(character)>0xffff else 1
            if ranges and ranges[-1].format.font()==font:
                ranges[-1].length+=length
            else:
                run=QTextLayout.FormatRange();run.start=offset;run.length=length
                run.format=QTextCharFormat();run.format.setFont(font);ranges.append(run)
            offset+=length
        return ranges

    def sizeHint(self,option,index):
        return QSize(300,42)

    def paint(self,painter,option,index):
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index)
        number=index.row()+1
        label='10(0)' if number==10 else str(number)
        text=f'{label}. {opt.text}';opt.text=''
        painter.save()
        widget=opt.widget
        style=widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem,opt,painter,widget)
        painter.setClipRect(option.rect)
        selected=bool(option.state&QStyle.StateFlag.State_Selected)
        painter.setPen(QColor('#214fba' if selected else '#172238'))
        layout=QTextLayout(text,self.fonts[0]);layout.setFormats(self.formats(text))
        layout.beginLayout();line=layout.createLine()
        if line.isValid():line.setLineWidth(100000)
        layout.endLayout()
        height=line.height() if line.isValid() else 20
        layout.draw(painter,QPointF(option.rect.left()+10,option.rect.top()+(option.rect.height()-height)/2))
        painter.restore()


class ReadingLabel(QLabel):
    """The reading header also needs bounded fallback for kana such as ー."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.renderer=CandidateDelegate(self,pixel_size=14)
        self.setFont(self.renderer.fonts[0]);self.setFixedHeight(24)

    def sizeHint(self):
        return QSize(300,24)

    def minimumSizeHint(self):
        return QSize(0,24)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setPen(QColor('#254a82'))
        layout=QTextLayout(self.text(),self.renderer.fonts[0])
        layout.setFormats(self.renderer.formats(self.text()))
        layout.beginLayout();line=layout.createLine()
        if line.isValid():line.setLineWidth(100000)
        layout.endLayout();layout.draw(painter,QPointF(0,0))
