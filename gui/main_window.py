from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QTextEdit,
    QProgressBar,
    QGridLayout,
    QMainWindow,
    QVBoxLayout,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFontComboBox,
    QLCDNumber,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QInputDialog,
    QDialog,
    QStackedWidget
)
from PySide6.QtCore import Qt, QThread, QSettings
import sys
import json
from pathlib import Path
from gui.workers.assemble_worker import AssembleWorker
from gui.screens.scan_screen import ScanScreen
from gui.screens.template_editor_screen import TemplateEditorScreen
from gui.screens.assemble_screen import AssembleScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Rebalance", "Ressemble")
        
        self.setWindowTitle("Ressemble")
        self.resize(700, 500)
        
        self.stack = QStackedWidget()
        
        self.scan_screen = ScanScreen(self, self.settings)
        self.template_editor_screen = TemplateEditorScreen(self, self.settings)
        self.assemble_screen = AssembleScreen(self, self.settings)
        
        self.stack.addWidget(self.scan_screen)
        self.stack.addWidget(self.template_editor_screen)
        self.stack.addWidget(self.assemble_screen)
        
        # layout.addWidget(self.assemble_button, 4, 1,)
        
        self.setCentralWidget(self.stack)
    
    def disable_actions(self):
        self.assemble_button.setEnabled(self.assemble_button.isEnabled() != True)