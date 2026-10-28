from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from gui.icons import pixmap
from gui.theme import repolish, OK


class SectionCard(QFrame):
    """A white card with a numbered title. The number turns into a green
    check once the section is complete (see set_done()), so a glance down
    the form shows what's left."""

    def __init__(self, number, title, hint=None, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._number = number

        outer = QVBoxLayout()
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)

        self.badge = QLabel(str(number))
        self.badge.setProperty("class", "badge")
        self.badge.setFixedSize(22, 22)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.badge)

        title_label = QLabel(title)
        title_label.setProperty("class", "card-title")
        header.addWidget(title_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setProperty("class", "status")
            header.addWidget(hint_label)

        header.addStretch(1)
        self.header_layout = header
        outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        outer.addLayout(self.body)

        self.setLayout(outer)

    def set_done(self, done):
        if done:
            self.badge.setText("")
            self.badge.setPixmap(pixmap("check", OK, 14))
        else:
            self.badge.setPixmap(QPixmap())
            self.badge.setText(str(self._number))
        self.badge.setProperty("state", "done" if done else "")
        repolish(self.badge)
