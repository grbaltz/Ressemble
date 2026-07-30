from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QLineEdit, QCheckBox
from PySide6.QtCore import QObject, Signal

class LabelDialog(QDialog):
    saveLabel = Signal(str)
    
    def __init__(self, filename):
        super().__init__()
        
        self.filename = filename
        
        self.setWindowTitle("Label Requested")

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        self.placeholder = QCheckBox("Placeholder?")
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.input = QLineEdit()

        layout = QVBoxLayout()
        message = QLabel(f"Please enter a Label for page: {filename}")
        layout.addWidget(message)
        layout.addWidget(self.input)
        layout.addWidget(self.placeholder)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
    
    def label(self):
        return self.input.text()
    
    def is_placeholder(self):
        return self.placeholder.isChecked()
