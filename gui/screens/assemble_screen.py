from PySide6.QtWidgets import QLabel, QDialog, QPushButton, QProgressBar, QTextEdit, QGridLayout, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QThread, QSettings
from pathlib import Path
import json
from gui.workers.assemble_worker import AssembleWorker

class AssembleScreen(QWidget):
    def __init__(self, main_window, settings):
        super().__init__()
        self.main_window = main_window
        self.settings = settings
        
        # Title
        self.title = QLabel("Generate Report")
        
        self.assemble_button = QPushButton("Assemble Report")
        self.assemble_button.clicked.connect(self.assemble)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(16)
        
        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.assemble_button)
        self.setLayout(layout)
        
    def assemble(self):
        self.thread = QThread()

        result = self.main_window.scan_results
        
        self.worker = AssembleWorker(
            matched_pages=result["matched_pages"],
            sources=result["sources"],
            advisors_file=result["advisors_file"],
        )
        
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)
        # self.worker.request_advisors.connect(self.request_advisors)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()