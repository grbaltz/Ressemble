from pathlib import Path
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from gui.icons import icon_label, icon, set_icon
from gui.widgets.drag_drop import dropped_file_path
from gui.widgets.elided_label import ElidedLabel
from gui.theme import repolish, ACCENT, ACCENT_TEXT, MUTED_TEXT


class FileSourceRow(QFrame):
    """One optional source file: a dashed drop target while empty, a file
    chip with a remove button once filled. Picking a file (browse button
    or drag-and-drop) only emits a signal -- the owning screen decides
    what to do with the path."""

    browse_clicked = Signal()
    file_dropped = Signal(str)
    cleared = Signal()

    def __init__(self, title, extensions, empty_hint="Drop a PDF here", parent=None):
        super().__init__(parent)
        self.setProperty("class", "source-row")
        self.setAcceptDrops(True)
        self._extensions = extensions
        self._empty_hint = empty_hint
        self._path = None

        self.icon = icon_label("upload", ACCENT, 20)

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "row-title")

        self.detail_label = ElidedLabel(empty_hint)
        self.detail_label.setProperty("class", "row-detail")

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        text.addWidget(self.title_label)
        text.addWidget(self.detail_label)

        self.browse_button = QPushButton("Browse")
        self.browse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.browse_button.clicked.connect(self.browse_clicked)

        self.clear_button = QPushButton()
        self.clear_button.setProperty("class", "icon-button")
        self.clear_button.setIcon(icon("x", MUTED_TEXT, 16))
        self.clear_button.setToolTip("Remove this file")
        self.clear_button.setAccessibleName(f"Remove {title}")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clear_button.clicked.connect(self.cleared)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self.icon)
        layout.addLayout(text, 1)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.clear_button)
        self.setLayout(layout)

        self.set_path(None)

    def path(self):
        return self._path

    def set_path(self, path, detail=None):
        """Shows `path` (or the empty drop target for None/""). `detail`
        replaces the filename line, e.g. with a page count."""
        self._path = path or None
        filled = self._path is not None

        if filled:
            set_icon(self.icon, "file-text", ACCENT_TEXT)
            self.detail_label.setText(detail or Path(self._path).name)
            self.detail_label.setToolTip(self._path)
        else:
            set_icon(self.icon, "upload", ACCENT)
            self.detail_label.setText(self._empty_hint)

        self.browse_button.setVisible(not filled)
        self.clear_button.setVisible(filled)
        self.setProperty("empty", "false" if filled else "true")
        repolish(self)

    def dragEnterEvent(self, event):
        if dropped_file_path(event.mimeData(), self._extensions):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._set_drag_active(False)
        path = dropped_file_path(event.mimeData(), self._extensions)
        if path:
            event.acceptProposedAction()
            self.file_dropped.emit(path)
        else:
            event.ignore()

    def _set_drag_active(self, active):
        self.setProperty("dragActive", "true" if active else "false")
        repolish(self)
