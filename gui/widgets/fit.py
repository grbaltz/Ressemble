from PySide6.QtWidgets import QStackedWidget, QScrollArea
from PySide6.QtCore import QSize, QEvent

# Used until the scroll area has been laid out once and knows its real width.
FALLBACK_WIDTH = 640


class CurrentStack(QStackedWidget):
    """A stacked widget that sizes itself to the page showing, not to the
    largest page it holds -- so a window built around it can fit whichever
    screen is currently visible."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentChanged.connect(lambda _: self.updateGeometry())

    def sizeHint(self):
        page = self.currentWidget()
        return page.sizeHint() if page is not None else super().sizeHint()

    def minimumSizeHint(self):
        page = self.currentWidget()
        return page.minimumSizeHint() if page is not None else super().minimumSizeHint()


class FitScrollArea(QScrollArea):
    """A scroll area that asks for as much height as its content needs.
    QScrollArea normally caps its size hint at a few dozen lines of text,
    which would force a scrollbar long before the screen runs out of room;
    here the scrollbar only appears when the window itself can't grow
    further."""

    def setWidget(self, widget):
        super().setWidget(widget)
        # The scroll area doesn't notice its content changing height on its
        # own, so tell whatever is sizing it to ask again.
        widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().eventFilter(watched, event)

    def sizeHint(self):
        content = self.widget()
        if content is None:
            return super().sizeHint()

        layout = content.layout()
        width = self.viewport().width()
        if width <= 0:
            width = FALLBACK_WIDTH

        if layout is not None and layout.hasHeightForWidth():
            height = layout.totalHeightForWidth(width)
        else:
            height = content.sizeHint().height()

        frame = 2 * self.frameWidth()
        return QSize(content.sizeHint().width() + frame, height + frame)
