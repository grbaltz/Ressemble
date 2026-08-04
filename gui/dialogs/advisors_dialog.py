from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QGridLayout, QLineEdit, QRadioButton, QComboBox, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QImage, QPixmap

ADVISOR_OPTIONS = [
    "Christie Whitney",
    "Dan Mavraides",
    "Kameron Javier",
    "Matt Jude",
    "Mitch Tuchman",
    "Sally Brandon",
    "Scott Puritz",
    "Sonja Breeding",
]

class AdvisorsDialog(QDialog):    
    def __init__(self):
        super().__init__()
        self._advisors = None
        
        self.setWindowTitle("Select Advisors")

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        
        self.list_widget = QListWidget()
        
        for advisor in ADVISOR_OPTIONS:
            item = QListWidgetItem(advisor)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        message = QLabel(f"Please select the assigned Advisors:")
        self.input = QLineEdit()

        layout = QGridLayout()
        layout.addWidget(message)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        
    def changed_selection(self, values):
        print(f"Selection changed: {values}")
        self._advisors = values
        
    def advisors(self):
        return self._advisors
