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
)
from PySide6.QtCore import Qt, QThread
from gui.worker import AssembleWorker, ScanWorker

import sys
import json
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("ReSemble")
        self.resize(700, 500)
        
        # Title
        self.title = QLabel()
        
        # Template select
            # Opens dialog after scanning 
        self.pdf_path = QLineEdit()
        browse_pdf = QPushButton("Browse")
        browse_pdf.clicked.connect(self.choose_pdf)

        # Client name input
        self.name_label = QLabel("Enter client name:")
        self.name_label.setAlignment(Qt.AlignRight)
        self.client_name = QLineEdit()
        # self.name_input.textChanged.connect(self.label.setText)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(16)
        
        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        
        # Assemble
        self.assemble_button = QPushButton("Assemble Report")
        self.assemble_button.clicked.connect(self.assemble)
        
        with open(Path("./src/template.json")) as template_config:
            config = json.load(template_config)
            
            if "filename" in config and config["filename"] != "":
                self.pdf_path.setText(config["filename"])
                self.scan_pdf()
                self.log.append("Test")
        
        layout = QGridLayout()
        layout.addWidget(self.title, 0, 0)
        
        layout.addWidget(browse_pdf, 1, 0)
        layout.addWidget(self.pdf_path, 1, 1)
        
        layout.addWidget(self.name_label, 2, 0)
        layout.addWidget(self.client_name, 2, 1)
        
        layout.addWidget(self.progress, 3, 0)

        layout.addWidget(self.log, 4, 0)
        
        layout.addWidget(self.assemble_button, 5, 0)
        
        container = QWidget()
        container.setLayout(layout)
        
        self.setCentralWidget(container)
        
    def choose_pdf(self):      
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if filename:
            self.pdf_path.setText(filename)
            
        self.scan_pdf()
            
    def scan_pdf(self):
        self.assemble_button.setEnabled(False)
        
        self.thread = QThread()
                
        self.worker = ScanWorker(
            pdf=self.pdf_path.text()
        )
        
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        
        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.assemble_button.setEnabled(True))
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()
    
    def disable_actions(self):
        self.assemble_button.setEnabled(self.assemble_button.isEnabled() != True)
        
    def assemble(self):
        self.thread = QThread()
        
        self.worker = AssembleWorker(
            pdf=self.pdf_path.text(),
            output="",
            client_name=self.client_name.text(),
        )
        
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

        # assemble_report(
        #     pdf=self.pdf_path.text(),
        #     output="",
        #     # output=self.output_path.text(),
        #     client_name=self.client_name.text(),
        #     log=self.log.append,
        # )
        # print("Mainwindow assemble report call")