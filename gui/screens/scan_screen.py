from PySide6.QtWidgets import QLabel, QPushButton, QProgressBar, QTextEdit, QFileDialog, QDialog
from PySide6.QtCore import Qt, QThread
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.collapsible import CollapsibleSection
from gui.workers.scan_worker import ScanWorker
from gui.dialogs.label_dialog import LabelDialog
from pathlib import Path
import json
from src.paths import TEMPLATE_CONFIG_PATH

class ScanScreen(WizardScreen):
    def __init__(self, main_window, settings):
        super().__init__("Preparing Report", "Scanning the report template for pages that need attention.")
        self.main_window = main_window
        self.settings = settings
        self._pdf_path = ""
        self._sources_and_advisors_connected = False

        # Driven automatically -- no continue button needed here.
        self.set_primary(visible=False)

        self.status_label = QLabel("Starting scan…")
        self.status_label.setProperty("class", "status")

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        self.details = CollapsibleSection("Details", self.log, collapsed=True)

        self.change_file_button = QPushButton("Use a different file…")
        self.change_file_button.setProperty("class", "link")
        self.change_file_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.change_file_button.clicked.connect(self.choose_pdf)

        self.content_layout.addWidget(self.status_label)
        self.content_layout.addWidget(self.progress)
        self.content_layout.addWidget(self.change_file_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.details)

        self._start()

    def _start(self):
        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                config = json.load(template_config)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}

        filename = config.get("filename")
        if filename:
            self._pdf_path = filename
            self.scan_pdf()
        else:
            self.choose_pdf()

    def choose_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Report PDF",
            self.settings.value("lastTemplateDir"),
            "PDF Files (*.pdf)"
        )

        if filename:
            self.settings.setValue("lastTemplateDir", str(Path(filename).parent))
            self._pdf_path = filename
            self.scan_pdf()

    def scan_pdf(self, refresh=False):
        self.status_label.setText("Starting scan…")
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.log.clear()

        self.thread = QThread()

        self.worker = ScanWorker(
            pdf=self._pdf_path,
            refresh=refresh
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.on_progress)
        self.worker.request_label.connect(self.request_label)
        self.worker.request_sources_and_advisors.connect(self.request_sources_and_advisors)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.on_scan_finished)

        self.thread.start()

    def on_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(f"Scanning page {current} of {total}…")

    def on_scan_finished(self, results):
        self.main_window.scan_results = results
        self.main_window.stack.setCurrentWidget(
            self.main_window.details_screen
        )

    def request_label(self, filename, pix_bytes):
        self.status_label.setText("New page found — needs a label…")

        dlg = LabelDialog(filename, pix_bytes)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.worker.receive_label(dlg.label())
        else:
            self.worker.receive_label(None)

    def request_sources_and_advisors(self):
        screen = self.main_window.sources_advisors_screen
        screen.reset()

        if self._sources_and_advisors_connected:
            screen.submitted.disconnect(self._on_sources_and_advisors_submitted)
        screen.submitted.connect(self._on_sources_and_advisors_submitted)
        self._sources_and_advisors_connected = True

        self.main_window.stack.setCurrentWidget(screen)

    def _on_sources_and_advisors_submitted(self, sources, advisors):
        self.main_window.stack.setCurrentWidget(self)
        self.status_label.setText("Finishing scan…")
        self.progress.setMaximum(0)
        self.worker.receive_sources_and_advisors(sources, advisors)
