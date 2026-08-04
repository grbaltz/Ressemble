from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit, QGridLayout, QWidget, QVBoxLayout
from pathlib import Path
import json

class TemplateEditorScreen(QWidget):
    def __init__(self, main_window, settings):
        super().__init__()
        
        # Title
        self.title = QLabel()