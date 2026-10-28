from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from gui.icons import icon_label, icon
from gui.theme import repolish, ON_ACCENT

HEADER_TEXT = "#E6E8EB"


class AppHeader(QFrame):
    """The charcoal bar across the top: product name on the left, a single
    button on the right that flips between the report builder and the
    Library, with a status dot showing whether the Library needs attention."""

    library_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "header")
        self.setFixedHeight(52)

        logo = icon_label("files", ON_ACCENT, 18)
        logo.setProperty("class", "logo-mark")
        logo.setFixedSize(28, 28)

        title = QLabel("Ressemble")
        title.setProperty("class", "header-title")

        self.dot = QLabel()
        self.dot.setProperty("class", "dot")
        self.dot.setFixedSize(8, 8)

        self.library_button = QPushButton()
        self.library_button.setProperty("class", "header-button")
        self.library_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.library_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.library_button.clicked.connect(self.library_clicked)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 12, 0)
        button_layout.addStretch(1)
        button_layout.addWidget(self.dot)
        self.library_button.setLayout(button_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self.library_button)
        self.setLayout(layout)

        self.show_library_button()
        self.set_status("ok", "Library is ready")

    def show_library_button(self):
        self.library_button.setText("Library")
        self.library_button.setIcon(icon("books", HEADER_TEXT, 16))
        self.library_button.setStyleSheet("QPushButton { padding-right: 32px; }")

    def show_back_button(self):
        self.library_button.setText("Back to report")
        self.library_button.setIcon(icon("arrow-left", HEADER_TEXT, 16))
        self.library_button.setStyleSheet("QPushButton { padding-right: 12px; }")

    def set_dot_visible(self, visible):
        self.dot.setVisible(visible)

    def set_status(self, state, tooltip=""):
        """state: "ok", "warn" or "busy" (scanning)."""
        self.dot.setProperty("state", state)
        repolish(self.dot)
        self.library_button.setToolTip(tooltip)
