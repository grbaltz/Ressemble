from PySide6.QtWidgets import QAbstractButton
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from gui.theme import ACCENT, BORDER_STRONG


class ToggleSwitch(QAbstractButton):
    """An on/off switch -- a checkable button drawn as a pill with a knob.
    QSS can't draw the knob, so it's painted by hand."""

    WIDTH = 34
    HEIGHT = 20

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def sizeHint(self):
        return QSize(self.WIDTH, self.HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track = QRectF(0, 0, self.WIDTH, self.HEIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ACCENT if self.isChecked() else BORDER_STRONG))
        painter.drawRoundedRect(track, self.HEIGHT / 2, self.HEIGHT / 2)

        knob_size = self.HEIGHT - 4
        knob_x = self.WIDTH - knob_size - 2 if self.isChecked() else 2
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QRectF(knob_x, 2, knob_size, knob_size))

        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(ACCENT), 1.5))
            painter.drawRoundedRect(track.adjusted(-1, -1, 1, 1), self.HEIGHT / 2 + 1, self.HEIGHT / 2 + 1)
