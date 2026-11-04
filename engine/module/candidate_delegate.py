"""Bounded font fallback for IME candidates, including emoji and rare kanji.

Qt's automatic fallback can scan the user's entire font collection for one
unsupported symbol. Select from explicit CJK/symbol fonts for each text run.
"""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QRawFont, QTextCharFormat, QTextLayout
from PySide6.QtWidgets import QApplication, QLabel, QStyle, QStyledItemDelegate, QStyleOptionViewItem


ROW_HEIGHT = 38


class CandidateDelegate(QStyledItemDelegate):
    def __init__(self,parent=None,pixel_size=18,dark=False):
        super().__init__(parent)
        self.dark=dark
        self.badge_font=QFont('Segoe UI')
        self.badge_font.setPixelSize(11)
        self.fonts=[];self.raw=[];self.cache={}
        for family in ('Malgun Gothic','Yu Gothic UI','Meiryo','Microsoft JhengHei UI','Microsoft YaHei UI',
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
        return QSize(300,ROW_HEIGHT)

    def paint(self,painter,option,index):
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index)
        number=index.row()+1
        label='0' if number==10 else str(number)
        text=opt.text;opt.text=''
        painter.save()
        widget=opt.widget
        style=widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem,opt,painter,widget)
        painter.setClipRect(option.rect)
        selected=bool(option.state&QStyle.StateFlag.State_Selected)
        badge=QRectF(option.rect.left()+7,option.rect.top()+(option.rect.height()-22)/2,24,22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(('#35527d' if selected else '#29303a') if self.dark else
                                ('#d4e4ff' if selected else '#edf0f4')))
        painter.drawRoundedRect(badge,5,5)
        painter.setFont(self.badge_font)
        painter.setPen(QColor(('#c0d6ff' if selected else '#b4bdca') if self.dark else
                              ('#244cac' if selected else '#4a576b')))
        painter.drawText(badge,Qt.AlignmentFlag.AlignCenter,label)
        painter.setPen(QColor(('#eef4ff' if selected else '#e8ecf2') if self.dark else
                              ('#163b91' if selected else '#172238')))
        layout=QTextLayout(text,self.fonts[0]);layout.setFormats(self.formats(text))
        layout.beginLayout();line=layout.createLine()
        if line.isValid():line.setLineWidth(100000)
        layout.endLayout()
        height=line.height() if line.isValid() else 20
        layout.draw(painter,QPointF(option.rect.left()+42,option.rect.top()+(option.rect.height()-height)/2))
        painter.restore()


class ReadingLabel(QLabel):
    """The reading header also needs bounded fallback for kana such as ー."""
    def __init__(self,parent=None,dark=False):
        super().__init__(parent)
        self.renderer=CandidateDelegate(self,pixel_size=14)
        self.color='#c1d5f5' if dark else '#405477'
        self.setFont(self.renderer.fonts[0]);self.setFixedHeight(24)

    def sizeHint(self):
        return QSize(300,24)

    def minimumSizeHint(self):
        return QSize(0,24)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setPen(QColor(self.color))
        layout=QTextLayout(self.text(),self.renderer.fonts[0])
        layout.setFormats(self.renderer.formats(self.text()))
        layout.beginLayout();line=layout.createLine()
        if line.isValid():line.setLineWidth(100000)
        layout.endLayout();layout.draw(painter,QPointF(0,0))
