from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from gui.icons import icon_label
from gui.theme import repolish, ACCENT_TEXT
from gui.widgets.drag_drop import dropped_file_path
from gui.widgets.elided_label import ElidedLabel
from gui.widgets.status_chip import StatusChip


class LibraryRow(QFrame):
    """One thing the Library holds (template, advisors, tear sheets): an
    icon, what it is, which file it came from, a status chip and its
    actions. Also a drop target for its own kind of file. `extra` is a
    layout under the main row for things like scan progress."""

    file_dropped = Signal(str)

    def __init__(self, icon_name, title, extensions, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setAcceptDrops(True)
        self._extensions = extensions

        tile = icon_label(icon_name, ACCENT_TEXT, 22)
        tile.setFixedSize(40, 40)
        tile.setProperty("class", "icon-tile")

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "row-title")

        self.file_label = ElidedLabel("")
        self.file_label.setProperty("class", "row-detail")

        self.note_label = QLabel("")
        self.note_label.setProperty("class", "row-detail")
        self.note_label.setWordWrap(True)
        self.note_label.setVisible(False)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        text.addWidget(self.title_label)
        text.addWidget(self.file_label)
        text.addWidget(self.note_label)

        self.chip = StatusChip("", "busy")

        self.buttons = QHBoxLayout()
        self.buttons.setContentsMargins(0, 0, 0, 0)
        self.buttons.setSpacing(8)

        main = QHBoxLayout()
        main.setSpacing(14)
        main.addWidget(tile, 0, Qt.AlignmentFlag.AlignTop)
        main.addLayout(text, 1)
        main.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignTop)
        main.addLayout(self.buttons)

        self.extra = QVBoxLayout()
        self.extra.setContentsMargins(0, 0, 0, 0)
        self.extra.setSpacing(8)

        outer = QVBoxLayout()
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)
        outer.addLayout(main)
        outer.addLayout(self.extra)
        self.setLayout(outer)

    def add_button(self, text, callback, primary=False):
        button = QPushButton(text)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if primary:
            button.setProperty("class", "primary")
        button.clicked.connect(callback)
        self.buttons.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)
        return button

    def set_file(self, text):
        self.file_label.setText(text)

    def set_note(self, text):
        self.note_label.setText(text)
        self.note_label.setVisible(bool(text))

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
