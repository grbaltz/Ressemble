from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit, QGridLayout, QWidget, QFileDialog, QDialog
from PySide6.QtCore import Qt, QThread, QSettings
from gui.workers.scan_worker import ScanWorker
from gui.dialogs.label_dialog import LabelDialog
from gui.dialogs.sources_dialog import SourcesDialog
from gui.dialogs.advisors_dialog import AdvisorsDialog
from pathlib import Path
import json

class ScanScreen(QWidget):
    def __init__(self, main_window, settings):
        super().__init__()
        self.main_window = main_window
        self.settings = settings
        
        # Title
        self.title = QLabel("Prepare Report")
        
        # Template select
        # Opens dialog after scanning 
        self.pdf_path = QLineEdit()
        browse_pdf = QPushButton("Browse")
        browse_pdf.clicked.connect(self.choose_pdf)
        
        # Refresh button
        self.rescan = QPushButton()
        self.rescan.setToolTip("Refresh Template")
        self.rescan.clicked.connect(lambda: self.scan_pdf(True))
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(16)
        
        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        
        # Assemble
        # self.assemble_button = QPushButton("Assemble Report")
        # self.assemble_button.clicked.connect(self.assemble)
        
        repo_root = Path(__file__).resolve().parent.parent.parent
        with open(repo_root / "src" / "template.json") as template_config:
            config = json.load(template_config)
            
            if "filename" in config and config["filename"] != "":
                self.pdf_path.setText(config["filename"])
                self.scan_pdf()
        
        layout = QGridLayout()
        layout.addWidget(self.title, 0, 0)
        
        layout.addWidget(browse_pdf, 1, 0)
        layout.addWidget(self.pdf_path, 1, 1)
        layout.addWidget(self.rescan, 1, 2)
        
        # layout.addWidget(self.name_label, 2, 0)
        # layout.addWidget(self.client_name, 2, 1)
        
        layout.addWidget(self.progress, 2, 0, 1, -1)

        layout.addWidget(self.log, 3, 0, 1, -1)
        
        self.setLayout(layout)
        
    def choose_pdf(self):      
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose PDF",
            self.settings.value("lastTemplateDir"),
            "PDF Files (*.pdf)"
        )
        

        if filename:
            self.settings.setValue("lastTemplateDir", str(Path(filename).parent))
            self.pdf_path.setText(filename)
            self.scan_pdf()
        
    def scan_pdf(self, refresh=False):
        # self.assemble_button.setEnabled(False)
        
        self.thread = QThread()
                
        self.worker = ScanWorker(
            pdf=self.pdf_path.text(),
            refresh=refresh
        )
        
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        
        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)        
        self.worker.request_label.connect(self.request_label)
        self.worker.request_sources.connect(self.request_sources)
        self.worker.request_advisors.connect(self.request_advisors)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.on_scan_finished)
        
        self.thread.start()
        
    def on_scan_finished(self, results):
        print("Finished scan pdf")

        self.main_window.scan_results = results
                
        self.main_window.stack.setCurrentWidget(
            self.main_window.assemble_screen
        )
    
    def request_label(self, filename, pix_bytes):
        print(f"-- Opening LabelDialog for filename {filename}")
        
        dlg = LabelDialog(filename, pix_bytes)
        if dlg.exec() == QDialog.Accepted:
            self.worker.receive_label(dlg.label())
            # self.worker.receive_label(dlg.label(), dlg.get_slot())
        else:
            self.worker.receive_label(None, False)        
        
    def request_sources(self):
        print(f"-- Opening SourcesDialog for")
        
        dlg = SourcesDialog()
        if dlg.exec() == QDialog.Accepted:
            self.worker.receive_sources(dlg.sources())
        else:
            self.worker.receive_sources(None)
            
    def request_advisors(self):
        print(f"-- Opening AdvisorsDialog")

        dlg = AdvisorsDialog()
        if dlg.exec() == QDialog.Accepted:
            self.worker.receive_advisors(dlg.advisors())
        else:
            self.worker.receive_advisors(None)