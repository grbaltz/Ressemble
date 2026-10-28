from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup
from PySide6.QtCore import Qt, Signal


class SegmentedControl(QFrame):
    """A row of mutually exclusive options joined into one bordered pill."""

    current_changed = Signal(int)

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setProperty("class", "segmented")

        layout = QHBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.setLayout(layout)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = []

        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setProperty("class", "segment")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._group.addButton(button, index)
            layout.addWidget(button)
            self._buttons.append(button)

        self._buttons[0].setChecked(True)
        self._group.idClicked.connect(self.current_changed)

    def current_index(self):
        return self._group.checkedId()

    def set_current_index(self, index):
        self._buttons[index].setChecked(True)
