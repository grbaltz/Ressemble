from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.collapsible import CollapsibleSection
from gui.workers.assemble_worker import AssembleWorker
from pathlib import Path

class CompileScreen(WizardScreen):
    def __init__(self, main_window, settings):
        super().__init__("Compiling Report", "Assembling the final PDF from the selected sources.")
        self.main_window = main_window
        self.settings = settings
        self._report_path = None

        self.content_layout.addWidget(self._build_compiling_state())
        self.content_layout.addWidget(self._build_done_state())

        self.set_primary(visible=False)

        self._show_compiling()

    def _build_compiling_state(self):
        self.compiling_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.status_label = QLabel("Starting…")
        self.status_label.setProperty("class", "status")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        layout.addWidget(CollapsibleSection("Details", self.log, collapsed=True))

        self.compiling_widget.setLayout(layout)
        return self.compiling_widget

    def _build_done_state(self):
        self.done_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.done_label = QLabel("Report ready.")
        self.done_label.setProperty("class", "status")
        layout.addWidget(self.done_label)

        self.path_field = QLineEdit()
        self.path_field.setReadOnly(True)
        layout.addWidget(self.path_field)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        self.open_pdf_button = QPushButton("Open PDF")
        self.open_pdf_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.open_pdf_button.clicked.connect(self._open_pdf)
        button_row.addWidget(self.open_pdf_button)

        self.show_folder_button = QPushButton("Show in Folder")
        self.show_folder_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.show_folder_button.clicked.connect(self._show_folder)
        button_row.addWidget(self.show_folder_button)

        button_row.addStretch(1)

        layout.addLayout(button_row)

        self.done_widget.setLayout(layout)
        return self.done_widget

    def _show_compiling(self):
        self.compiling_widget.setVisible(True)
        self.done_widget.setVisible(False)
        self.set_title("Compiling Report")
        self.set_subtitle("Assembling the final PDF from the selected sources.")
        self.set_primary(visible=False)

    def _show_done(self, report_path):
        self.compiling_widget.setVisible(False)
        self.done_widget.setVisible(True)
        self.set_title("Report Ready")
        self.set_subtitle("The report has been compiled and saved to the location below.")
        self.path_field.setText(str(report_path))
        self.set_primary("Start New Report", enabled=True, callback=self._new_report, visible=True)

    def start(self):
        self._show_compiling()
        self.status_label.setText("Starting…")
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.log.clear()

        result = self.main_window.scan_results

        self.thread = QThread()

        self.worker = AssembleWorker(
            matched_pages=result["matched_pages"],
            sources=result["sources"],
            advisors_file=result["advisors_file"],
            client_name=self.main_window.client_name,
            enrolled=self.main_window.enrolled,
            target_date=self.main_window.target_date,
            include_page_numbers=self.main_window.include_page_numbers,
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.on_progress)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.on_finished)

        self.thread.start()

    def on_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(f"Compiling page {current} of {total}…")

    def on_finished(self, report_path):
        self._report_path = report_path
        if report_path:
            self._show_done(report_path)
        else:
            self.status_label.setText("Something went wrong — check details below.")

    def _open_pdf(self):
        if self._report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._report_path)))

    def _show_folder(self):
        if self._report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self._report_path).parent)))

    def _new_report(self):
        self.main_window.restart()

    def reset(self):
        self._report_path = None
        self.path_field.clear()
        self._show_compiling()
