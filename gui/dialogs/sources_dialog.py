from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QLineEdit, QCheckBox, QPushButton, QFileDialog
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtGui import QImage, QPixmap
from pathlib import Path

settings = QSettings("Rebalance", "ReSemble")

class SourcesDialog(QDialog):    
    def __init__(self):
        super().__init__()
    
        self._sources = [None, None]
        
        self.setWindowTitle("Select EMX/BD Files")

        self.browse_emx = QPushButton("Select")
        self.browse_emx.clicked.connect(lambda: self.choose_sources("emx"))
        self.browse_bd = QPushButton("Select")
        self.browse_bd.clicked.connect(lambda: self.choose_sources("bd"))

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept_sources)
        self.buttonBox.rejected.connect(self.reject)        

        layout = QVBoxLayout()
        # layout.addWidget(label)
        layout.addWidget(QLabel("Select EMX PDF"))
        layout.addWidget(self.browse_emx)
        layout.addWidget(QLabel("Select Black Diamond PDF"))
        layout.addWidget(self.browse_bd)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        
    def choose_sources(self, slot):
        message = "" 
        if slot == "emx":
            message = "EMX"
        else:
            message = "Black Diamond"
            
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {message} PDF",
            settings.value("lastReplacementDir"),
            "PDF File (*.pdf)"
        )
        
        print(f"filename: {filename}")
        settings.setValue("lastReplacementDir", str(Path(filename).parent))

        if slot == "emx":
            self._sources[0] = filename
        else:
            self._sources[1] = filename

        
    
    def sources(self):
        return self._sources
    
    def accept_sources(self):
        if not self._sources:
            self._sources = []
        self.accept()
