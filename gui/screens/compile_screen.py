from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt, QThread, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.collapsible import CollapsibleSection
from gui.workers.assemble_worker import AssembleWorker
from pathlib import Path

# How long compiling may go without any progress or log output before the
# user is offered a retry. Compiling keeps going in the meantime -- it may
# just be a slow merge -- so this only prompts, it never kills the run.
STALL_TIMEOUT_MS = 20_000

class CompileScreen(WizardScreen):
    def __init__(self, main_window, settings):
        super().__init__("Compiling Report", "Assembling the final PDF from the selected sources.")
        self.main_window = main_window
        self.settings = settings
        self._report_path = None
        self._status_text = ""
        self._stalled = False

        self.worker = None
        # (thread, worker) pairs kept referenced until their thread stops,
        # so a cancelled run can wind down after a retry has replaced it.
        self._jobs = []

        self._stall_timer = QTimer(self)
        self._stall_timer.setSingleShot(True)
        self._stall_timer.setInterval(STALL_TIMEOUT_MS)
        self._stall_timer.timeout.connect(self._on_stalled)

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
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self.retry_button = QPushButton("Try Again")
        self.retry_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.retry_button.clicked.connect(self.start)
        action_row.addWidget(self.retry_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.cancel_button.clicked.connect(self._cancel)
        action_row.addWidget(self.cancel_button)

        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        self.details = CollapsibleSection("Details", self.log, collapsed=True)
        layout.addWidget(self.details)

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
        # Leaving mid-compile goes through Cancel, so Back is only offered
        # once there's nothing left running.
        self.set_back(visible=False)
        self.retry_button.setVisible(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)

    def _show_done(self, report_path):
        self.compiling_widget.setVisible(False)
        self.done_widget.setVisible(True)
        self.set_title("Report Ready")
        self.set_subtitle("The report has been compiled and saved to the location below.")
        self.path_field.setText(str(report_path))
        self.set_primary("Start New Report", enabled=True, callback=self._new_report, visible=True)
        self.set_back(callback=self._on_back, visible=True)

    def _show_failed(self, message):
        self._set_status(message)
        # A determinate, empty bar -- the busy animation would suggest
        # something is still happening.
        self.progress.setMaximum(1)
        self.progress.setValue(0)
        self.retry_button.setVisible(True)
        self.cancel_button.setVisible(False)
        self.details.set_collapsed(False)
        self.set_back(callback=self._on_back, visible=True)

    def _set_status(self, text):
        self._status_text = text
        self.status_label.setText(text)

    def start(self):
        # Also serves as "Try Again" -- any run still going is cancelled
        # first, and its late signals are ignored (see _is_current).
        self._stop_worker()
        self._prune_jobs()

        self._show_compiling()
        self._set_status("Starting…")
        self._stalled = False
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.log.clear()

        result = self.main_window.scan_results

        thread = QThread()

        worker = AssembleWorker(
            matched_pages=result["matched_pages"],
            sources=result["sources"],
            advisors_file=result["advisors_file"],
            client_name=self.main_window.client_name,
            enrolled=self.main_window.enrolled,
            target_date=self.main_window.target_date,
            include_page_numbers=self.main_window.include_page_numbers,
            include_plan_360=self.main_window.include_plan_360,
        )

        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        worker.log.connect(self.on_log)
        worker.progress.connect(self.on_progress)

        worker.finished.connect(thread.quit)
        worker.finished.connect(self.on_finished)

        self.worker = worker
        self._jobs.append((thread, worker))
        thread.start()
        self._stall_timer.start()

    def _is_current(self):
        return self.worker is not None and self.sender() is self.worker

    def on_log(self, message):
        if not self._is_current():
            return
        self.log.append(message)
        self._on_activity()

    def on_progress(self, current, total):
        if not self._is_current():
            return
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        if current >= total:
            # Past the last template page, the merge and save still have
            # to run -- say so rather than sitting on "page N of N".
            self._set_status("Merging pages and saving the report…")
        else:
            self._set_status(f"Compiling page {current} of {total}…")
        self._on_activity()

    def _on_activity(self):
        self._stall_timer.start()
        if self._stalled:
            self._stalled = False
            self.retry_button.setVisible(False)
            self.status_label.setText(self._status_text)

    def _on_stalled(self):
        if self.worker is None:
            return
        self._stalled = True
        self.status_label.setText(
            f"No progress in the last {STALL_TIMEOUT_MS // 1000} seconds. Compiling may be stuck. "
            "You can keep waiting, try again, or cancel."
        )
        self.retry_button.setVisible(True)
        self.details.set_collapsed(False)

    def on_finished(self, report_path):
        if not self._is_current():
            return
        cancelled = self.worker._cancelled
        self.worker = None
        self._stall_timer.stop()
        self._stalled = False
        self._report_path = report_path
        if report_path:
            self._show_done(report_path)
        elif cancelled:
            self._show_failed("Compiling cancelled.")
        else:
            self._show_failed("Something went wrong. Check the details below, then try again.")

    def _cancel(self):
        if self.worker is None:
            return
        self.cancel_button.setEnabled(False)
        self._set_status("Cancelling…")
        self._stall_timer.stop()
        self.worker.cancel()

    def _stop_worker(self):
        self._stall_timer.stop()
        if self.worker is not None:
            self.worker.cancel()
            self.worker = None

    def _prune_jobs(self):
        self._jobs = [(thread, worker) for thread, worker in self._jobs if thread.isRunning()]

    def _open_pdf(self):
        if self._report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._report_path)))

    def _show_folder(self):
        if self._report_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self._report_path).parent)))

    def _new_report(self):
        self.main_window.restart()

    def _on_back(self):
        self.main_window.stack.setCurrentWidget(self.main_window.details_screen)

    def reset(self):
        self._stop_worker()
        self._report_path = None
        self.path_field.clear()
        self.details.set_collapsed(True)
        self._show_compiling()
