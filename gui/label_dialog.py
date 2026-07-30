from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QLineEdit, QCheckBox
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QImage, QPixmap

class LabelDialog(QDialog):    
    def __init__(self, filename, pix_bytes):
        super().__init__()
        
        self.filename = filename
        
        self.setWindowTitle("Label Requested")

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        self.placeholder = QCheckBox("Placeholder?")
        
        image = QImage()
        image.loadFromData(pix_bytes)
        pixmap = QPixmap.fromImage(image)
        label = QLabel()
        label.setPixmap(pixmap)
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        message = QLabel(f"Please provide a label for above page:")
        self.input = QLineEdit()

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(message)
        layout.addWidget(self.input)
        layout.addWidget(self.placeholder, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
    
    def label(self):
        return self.input.text()
    
    def is_placeholder(self):
        return self.placeholder.isChecked()
