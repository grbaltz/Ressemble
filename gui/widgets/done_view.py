from pathlib import Path
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from gui.icons import icon_label, icon
from gui.theme import OK, ON_ACCENT, TEXT
from gui.widgets.elided_label import ElidedLabel


class DoneView(QWidget):
    """Shown in place of the form once the report is saved."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report_path = None

        mark = icon_label("check", OK, 34)
        mark.setFixedSize(64, 64)
        mark.setProperty("class", "done-mark")

        title = QLabel("Report ready")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.path_label = ElidedLabel("")
        self.path_label.setProperty("class", "subtitle")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.open_button = QPushButton("Open report")
        self.open_button.setProperty("class", "primary")
        self.open_button.setIcon(icon("external-link", ON_ACCENT, 16))
        self.open_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.open_button.clicked.connect(self._open_pdf)

        self.folder_button = QPushButton("Show in folder")
        self.folder_button.setIcon(icon("folder", TEXT, 16))
        self.folder_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.folder_button.clicked.connect(self._show_folder)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.folder_button)
        buttons.addStretch(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 70, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(title)
        layout.addWidget(self.path_label)
        layout.addSpacing(14)
        layout.addLayout(buttons)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_report(self, report_path):
        self._report_path = str(report_path)
        self.path_label.setText(self._report_path)

    def _open_pdf(self):
        if self._report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._report_path))

    def _show_folder(self):
        if self._report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self._report_path).parent)))
