from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt


class CollapsibleSection(QWidget):
    """A toggle button that shows/hides a content widget beneath it.

    Used to tuck the raw scan/compile log out of the way by default while
    keeping it one click away for troubleshooting.
    """

    def __init__(self, title, content, collapsed=True):
        super().__init__()

        self._collapsed_text = f"▸  {title}"
        self._expanded_text = f"▾  {title}"

        self.toggle_button = QPushButton()
        self.toggle_button.setProperty("class", "toggle")
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggle_button.clicked.connect(self.toggle)

        self.content = content

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        self.setLayout(layout)

        self.set_collapsed(collapsed)

    def toggle(self):
        self.set_collapsed(self.content.isVisible())

    def set_collapsed(self, collapsed):
        self.content.setVisible(not collapsed)
        self.toggle_button.setText(self._collapsed_text if collapsed else self._expanded_text)
