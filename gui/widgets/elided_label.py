from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt, QSize


class ElidedLabel(QLabel):
    """A single-line label that shortens long text (file paths, names) with
    an ellipsis instead of demanding the width to show it -- so a long
    filename can never stretch the fixed-size window's layout. The full
    text stays available as a tooltip."""

    def __init__(self, text="", elide=Qt.TextElideMode.ElideMiddle, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._elide = elide
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text):
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        self._update_elided()

    def fullText(self):
        return self._full_text

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def sizeHint(self):
        return QSize(self.fontMetrics().horizontalAdvance(self._full_text), super().sizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        elided = self.fontMetrics().elidedText(self._full_text, self._elide, max(self.width(), 0))
        super().setText(elided)
