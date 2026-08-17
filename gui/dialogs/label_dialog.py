from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QLineEdit
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

class LabelDialog(QDialog):
    def __init__(self, filename, pix_bytes):
        super().__init__()

        self.filename = filename

        self.setWindowTitle("Label New Page")

        title = QLabel("This page wasn't recognized")
        title.setProperty("class", "title")

        message = QLabel(f"Give it a short label so it can be matched next time:")
        message.setProperty("class", "subtitle")
        message.setWordWrap(True)

        image = QImage()
        image.loadFromData(pix_bytes)
        pixmap = QPixmap.fromImage(image)
        preview = QLabel()
        preview.setPixmap(pixmap)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet("border: 1px solid #E1E4E8; border-radius: 6px; padding: 4px; background: white;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("e.g. Disclosures")
        self.input.returnPressed.connect(self.accept)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        layout.addWidget(self.input)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

        self.input.setFocus()

    def label(self):
        return self.input.text()
