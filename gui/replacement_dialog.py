from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QLineEdit, QCheckBox, QPushButton, QFileDialog
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtGui import QImage, QPixmap
from pathlib import Path

settings = QSettings("Rebalance", "ReSemble")

class ReplacementDialog(QDialog):    
    def __init__(self, filename, pix_bytes):
        super().__init__()
        
        self.filename = filename
        self.replacement_filenames = None
        
        self.setWindowTitle("Select files to insert")
        
        image = QImage()
        image.loadFromData(pix_bytes)
        pixmap = QPixmap.fromImage(image)
        label = QLabel()
        label.setPixmap(pixmap)

        self.browse_pdfs = QPushButton("Select")
        self.browse_pdfs.clicked.connect(self.choose_replacements)

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)        

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.browse_pdfs)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        
    def choose_replacements(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Select one or more PDFs to insert",
            settings.value("lastReplacementDir"),
            "PDF Files (*.pdf)"
        )
        
        print(f"filenames[0]: {filenames[0]}")
        settings.setValue("lastReplacementDir", str(Path(filenames[0]).parent))

        if len(filenames) > 0:
            self.replacement_filenames = filenames
    
    def replacements(self):
        return self.replacement_filenames
