import os
import pymupdf
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPixmap

# Longest side of the shown page, in logical pixels. Rendered at twice that
# and tagged with a device pixel ratio so it stays sharp on high-DPI screens.
MAX_SIDE = 380
SCALE = 2

_cache = {}


def render_page(pdf_path, page_number):
    """One page of a PDF as a pixmap, or None if it can't be read. Cached by
    file and modification time, since hovering the same row repeatedly
    shouldn't re-render the page each time."""
    try:
        key = (pdf_path, page_number, os.path.getmtime(pdf_path))
    except OSError:
        return None

    if key in _cache:
        return _cache[key]

    pixmap = None
    try:
        with pymupdf.open(pdf_path) as doc:
            page = doc[page_number]
            zoom = MAX_SIDE * SCALE / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(image)
            pixmap.setDevicePixelRatio(SCALE)
    except Exception:
        pixmap = None

    _cache[key] = pixmap
    return pixmap


class PagePreviewPopup(QFrame):
    """A small floating picture of one page, shown beside whatever the
    pointer is resting on. Never takes focus or mouse events, so it can't
    interfere with the hover that opened it."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setProperty("class", "preview-popup")

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._label)
        self.setLayout(layout)

    def show_beside(self, preview, anchor, row):
        """Shows `preview` (a PagePreview) to the left of `anchor` (the
        panel), vertically centered on `row` (the line being hovered).
        Returns False, showing nothing, if the page can't be rendered."""
        pixmap = render_page(preview.pdf_path, preview.page)
        if pixmap is None:
            return False

        self._label.setPixmap(pixmap)
        self.adjustSize()

        x = anchor.mapToGlobal(QPoint(0, 0)).x() - self.width() - 10
        y = row.mapToGlobal(QPoint(0, 0)).y() + row.height() // 2 - self.height() // 2

        screen = anchor.screen() or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        x = max(bounds.left() + 4, x)
        y = min(max(bounds.top() + 4, y), bounds.bottom() - self.height() - 4)

        self.move(x, y)
        self.show()
        return True
