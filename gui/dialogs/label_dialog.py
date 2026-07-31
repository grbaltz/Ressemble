from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QGridLayout, QLineEdit, QRadioButton, QComboBox
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QImage, QPixmap

class LabelDialog(QDialog):    
    def __init__(self, filename, pix_bytes):
        super().__init__()
        
        self.filename = filename
        self.slot = ""
        
        self.setWindowTitle("Label Requested")

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        self.slots = QComboBox()
        self.slots.addItems(["Normal", "EMX", "Black Diamond"])
        self.slots.currentTextChanged.connect(self.changed_slot)
        
        # self.slot_label = QLabel("Is Placeholder For:")
        # self.emx = QRadioButton("EMX files")
        # self.emx.toggled.connect(lambda: self.btnstate(self.emx))
        # self.bd = QRadioButton("Black Diamond files")
        # self.bd.toggled.connect(lambda: self.btnstate(self.bd))
        
        print(f"type {type(pix_bytes)}")
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

        layout = QGridLayout()
        layout.addWidget(label, 1, 0, 1, -1)
        layout.addWidget(message, 2, 0, 1, -1)
        layout.addWidget(self.input, 3, 0, 1, -1)
        layout.addWidget(self.slots, 4, 1, 1, 1)
        # layout.addWidget(self.emx, 5, 0)
        # layout.addWidget(self.bd, 5, 1)
        # layout.addWidget(self.placeholder, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.buttonBox, 5, 0, 1, -1)
        self.setLayout(layout)
        
    def changed_slot(self, text):
        if not text == "Normal":
            self.slot = text
        else:
            self.slot = ""
    
    def label(self):
        return self.input.text()
    
    def get_slot(self):
        return self.slot
