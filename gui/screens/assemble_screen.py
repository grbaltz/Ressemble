from PySide6.QtWidgets import QLabel, QDialog, QPushButton, QProgressBar, QTextEdit, QGridLayout, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QThread, QSettings
from pathlib import Path
import json
from gui.workers.assemble_worker import AssembleWorker
from gui.dialogs.advisors_dialog import AdvisorsDialog

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
        
        self.worker = AssembleWorker()
        
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.request_advisors.connect(self.request_advisors)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()
        
    def request_advisors(self, dir):
        print(f"-- Opening AdvisorsDialog")

        dlg = AdvisorsDialog()
        if dlg.exec() == QDialog.Accepted:
            self.worker.receive_advisors(dlg.advisors())
        else:
            self.worker.receive_advisors(None)