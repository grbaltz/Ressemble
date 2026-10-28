from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QProgressBar, QTextEdit, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal
from gui.icons import icon_label
from gui.theme import WARN_TEXT
from gui.widgets.collapsible import CollapsibleSection


class BuildView(QWidget):
    """Shown in place of the form while a report builds: what's happening,
    a progress bar, the "taking longer than usual" prompt, and the log.
    Cancel lives on the summary panel's button, not here."""

    retry_clicked = Signal()
    keep_waiting_clicked = Signal()
    edit_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title_label = QLabel("Building your report")
        self.title_label.setProperty("class", "title")

        self.subtitle_label = QLabel("")
        self.subtitle_label.setProperty("class", "subtitle")

        self.status_label = QLabel("Starting…")
        self.status_label.setProperty("class", "row-title")
        self.status_label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 14, 16, 16)
        card_layout.setSpacing(10)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.progress)
        card.setLayout(card_layout)

        self.stall_banner = self._build_stall_banner()
        self.stall_banner.setVisible(False)

        self.failed_row = QWidget()
        failed_layout = QHBoxLayout()
        failed_layout.setContentsMargins(0, 0, 0, 0)
        failed_layout.setSpacing(10)
        self.try_again_button = QPushButton("Try again")
        self.try_again_button.setProperty("class", "primary")
        self.try_again_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.try_again_button.clicked.connect(self.retry_clicked)
        edit_button = QPushButton("Edit details")
        edit_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        edit_button.clicked.connect(self.edit_clicked)
        failed_layout.addWidget(self.try_again_button)
        failed_layout.addWidget(edit_button)
        failed_layout.addStretch(1)
        self.failed_row.setLayout(failed_layout)
        self.failed_row.setVisible(False)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        self.details = CollapsibleSection("Details", self.log, collapsed=True)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(card)
        layout.addWidget(self.stall_banner)
        layout.addWidget(self.failed_row)
        layout.addWidget(self.details)
        layout.addStretch(1)
        self.setLayout(layout)

    def _build_stall_banner(self):
        banner = QFrame()
        banner.setProperty("class", "banner")

        message = QLabel("This is taking longer than usual")
        message.setProperty("class", "row-title")
        hint = QLabel("Large reports can take a while. You can keep waiting, or start over.")
        hint.setWordWrap(True)

        keep = QPushButton("Keep waiting")
        keep.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        keep.clicked.connect(self.keep_waiting_clicked)
        again = QPushButton("Try again")
        again.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        again.clicked.connect(self.retry_clicked)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(keep)
        buttons.addWidget(again)
        buttons.addStretch(1)

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(message)
        text.addWidget(hint)
        text.addSpacing(6)
        text.addLayout(buttons)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(icon_label("alert-triangle", WARN_TEXT, 20), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text, 1)
        banner.setLayout(layout)
        return banner

    def reset(self, client_name):
        self.title_label.setText(f"Building the {client_name} report" if client_name else "Building your report")
        self.subtitle_label.setText("Merging pages and saving. This usually takes under a minute.")
        self.status_label.setText("Starting…")
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.log.clear()
        self.details.set_collapsed(True)
        self.set_stalled(False)
        self.failed_row.setVisible(False)

    def set_status(self, text):
        self.status_label.setText(text)

    def set_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def append_log(self, text):
        self.log.append(text)

    def set_stalled(self, stalled):
        self.stall_banner.setVisible(stalled)
        if stalled:
            self.details.set_collapsed(False)

    def show_failed(self, message):
        """A determinate, empty bar -- the busy animation would suggest
        something is still happening."""
        self.status_label.setText(message)
        self.subtitle_label.setText("Nothing was saved.")
        self.progress.setMaximum(1)
        self.progress.setValue(0)
        self.stall_banner.setVisible(False)
        self.failed_row.setVisible(True)
        self.details.set_collapsed(False)
