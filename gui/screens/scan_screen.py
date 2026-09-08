from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QFileDialog,
    QDialog,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QThread
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.drag_drop import FileDropTargetMixin
from gui.widgets.file_drop_line_edit import FileDropLineEdit
from gui.workers.scan_worker import ScanWorker
from gui.dialogs.label_dialog import LabelDialog
from pathlib import Path
import json
from src.paths import TEMPLATE_CONFIG_PATH
from src.advisors import ensure_advisors_split, load_cached_advisors
from src.tear_sheets import ensure_tear_sheets_split, load_cached_tear_sheets

TEMPLATE_EXTENSIONS = {".pdf"}
ADVISORS_EXTENSIONS = {".pdf"}
TEAR_SHEETS_EXTENSIONS = {".pdf"}

class ScanScreen(FileDropTargetMixin, WizardScreen):
    """Handles everything that's independent of a specific report: the
    template itself, the advisors roster, and the tear sheets. All three
    are fingerprinted/split once and cached, and re-done automatically
    only when the provided file changes (which advisors apply to THIS
    report, and which tear sheets get inserted, is decided later based on
    the models actually present -- see Sources & Advisors and
    assembler.py). Once everything's in place, Continue hands off there --
    this screen otherwise only ever appears on app launch or via an
    explicit Back.
    """

    def __init__(self, main_window, settings):
        super().__init__("Preparing Report", "Scanning the report template for pages that need attention.")
        self.main_window = main_window
        self.settings = settings
        self._pdf_path = ""
        self._enable_file_drop(TEMPLATE_EXTENSIONS)

        # Always visible -- only ever disabled while a scan is actively
        # running. Its callback is re-pointed at whatever the current phase's
        # next step is (start over, or continue to Sources & Advisors)
        # rather than toggling visibility per phase.
        self.set_primary(text="Continue", enabled=False, callback=self.choose_pdf)

        self.status_label = QLabel("Starting scan…")
        self.status_label.setProperty("class", "status")

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        # QTextEdit accepts drops itself by default (for its own text
        # editing) -- disabled so a dropped template file reliably bubbles
        # up to this screen's own drop handler instead of being swallowed here.
        self.log.setAcceptDrops(False)
        self.details = CollapsibleSection("Details", self.log, collapsed=True)

        self.change_file_button = QPushButton("Use a different file…")
        self.change_file_button.setProperty("class", "link")
        self.change_file_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.change_file_button.clicked.connect(self.choose_pdf)

        self.advisors_label = QLabel("ADVISORS FILE")
        self.advisors_label.setProperty("class", "section")

        self.advisors_field = FileDropLineEdit(ADVISORS_EXTENSIONS)
        self.advisors_field.setReadOnly(True)
        self.advisors_field.setPlaceholderText("No advisors file selected -- drag a file here or browse")
        self.advisors_field.file_dropped.connect(self._use_advisors_pdf)

        self.advisors_browse_button = QPushButton("Browse…")
        self.advisors_browse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.advisors_browse_button.clicked.connect(self.choose_advisors_pdf)

        advisors_row = QHBoxLayout()
        advisors_row.setSpacing(8)
        advisors_row.addWidget(self.advisors_field, 1)
        advisors_row.addWidget(self.advisors_browse_button)

        self.advisors_status_label = QLabel("")
        self.advisors_status_label.setProperty("class", "status")
        self.advisors_status_label.setWordWrap(True)

        self.tear_sheets_label = QLabel("TEAR SHEETS FILE")
        self.tear_sheets_label.setProperty("class", "section")

        self.tear_sheets_field = FileDropLineEdit(TEAR_SHEETS_EXTENSIONS)
        self.tear_sheets_field.setReadOnly(True)
        self.tear_sheets_field.setPlaceholderText("No tear sheets file selected -- drag a file here or browse")
        self.tear_sheets_field.file_dropped.connect(self._use_tear_sheets_pdf)

        self.tear_sheets_browse_button = QPushButton("Browse…")
        self.tear_sheets_browse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tear_sheets_browse_button.clicked.connect(self.choose_tear_sheets_pdf)

        tear_sheets_row = QHBoxLayout()
        tear_sheets_row.setSpacing(8)
        tear_sheets_row.addWidget(self.tear_sheets_field, 1)
        tear_sheets_row.addWidget(self.tear_sheets_browse_button)

        self.tear_sheets_status_label = QLabel("")
        self.tear_sheets_status_label.setProperty("class", "status")
        self.tear_sheets_status_label.setWordWrap(True)

        self.content_layout.addWidget(self.status_label)
        self.content_layout.addWidget(self.progress)
        self.content_layout.addWidget(self.change_file_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.advisors_label)
        self.content_layout.addLayout(advisors_row)
        self.content_layout.addWidget(self.advisors_status_label)
        self.content_layout.addWidget(self.tear_sheets_label)
        self.content_layout.addLayout(tear_sheets_row)
        self.content_layout.addWidget(self.tear_sheets_status_label)
        self.content_layout.addWidget(self.details)

        self._start()

    def _start(self):
        self._load_cached_advisors_display()
        self._load_cached_tear_sheets_display()

        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                config = json.load(template_config)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}

        filename = config.get("filename")
        if filename:
            self._pdf_path = filename
            self.scan_pdf()
        # else: no template on file yet -- MainWindow shows
        # SelectTemplateScreen instead of this one in that case, which
        # hands off to start_with() once the user picks one.

    def start_with(self, pdf_path):
        self._pdf_path = pdf_path
        self.scan_pdf()

    def choose_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Report PDF",
            self.settings.value("lastTemplateDir"),
            "PDF Files (*.pdf)"
        )

        if filename:
            self._use_pdf(filename)

    def _handle_dropped_file(self, path):
        self._use_pdf(path)

    def _use_pdf(self, filename):
        self.settings.setValue("lastTemplateDir", str(Path(filename).parent))
        self._pdf_path = filename
        self.scan_pdf()

    def _load_cached_advisors_display(self):
        cached_source, cached_names = load_cached_advisors()
        if cached_source:
            self.advisors_field.setText(cached_source)
        self._set_advisors_status(cached_names)

    def choose_advisors_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Advisors PDF",
            self.settings.value("lastAdvisorsDir"),
            "PDF Files (*.pdf)"
        )

        if filename:
            self.settings.setValue("lastAdvisorsDir", str(Path(filename).parent))
            self._use_advisors_pdf(filename)

    def _use_advisors_pdf(self, filename):
        self.advisors_field.setText(filename)

        # Re-splitting is skipped internally if this is the same file as
        # last time, so it's safe to call unconditionally on every
        # selection/drop rather than tracking "did this actually change"
        # ourselves.
        try:
            names = ensure_advisors_split(filename)
        except Exception as exc:
            self.advisors_status_label.setText(f"Couldn't read advisors from that file: {exc}")
            return

        self._set_advisors_status(names)

    def _set_advisors_status(self, names):
        if names:
            plural = "s" if len(names) != 1 else ""
            self.advisors_status_label.setText(f"{len(names)} advisor{plural} found: {', '.join(names)}")
        elif self.advisors_field.text():
            self.advisors_status_label.setText("No advisors found in that file.")
        else:
            self.advisors_status_label.setText("")

    def _load_cached_tear_sheets_display(self):
        cached_source, cached_models = load_cached_tear_sheets()
        if cached_source:
            self.tear_sheets_field.setText(cached_source)
        self._set_tear_sheets_status(cached_models)

    def choose_tear_sheets_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Tear Sheets PDF",
            self.settings.value("lastTearSheetsDir"),
            "PDF Files (*.pdf)"
        )

        if filename:
            self.settings.setValue("lastTearSheetsDir", str(Path(filename).parent))
            self._use_tear_sheets_pdf(filename)

    def _use_tear_sheets_pdf(self, filename):
        self.tear_sheets_field.setText(filename)

        # Re-splitting is skipped internally if this is the same file as
        # last time, so it's safe to call unconditionally on every
        # selection/drop rather than tracking "did this actually change"
        # ourselves.
        try:
            models = ensure_tear_sheets_split(filename)
        except Exception as exc:
            self.tear_sheets_status_label.setText(f"Couldn't read tear sheets from that file: {exc}")
            return

        self._set_tear_sheets_status(models)

    def _set_tear_sheets_status(self, models):
        if models:
            plural = "s" if len(models) != 1 else ""
            self.tear_sheets_status_label.setText(f"{len(models)} tear sheet{plural} found: {', '.join(models)}")
        elif self.tear_sheets_field.text():
            self.tear_sheets_status_label.setText("No tear sheets found in that file.")
        else:
            self.tear_sheets_status_label.setText("")

    def scan_pdf(self, refresh=False):
        self.status_label.setText("Starting scan…")
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.log.clear()
        self.set_primary(enabled=False)
        self.change_file_button.setText("Use a different file…")

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

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.on_scan_finished)

        self.thread.start()

    def on_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(f"Scanning page {current} of {total}…")

    def on_scan_finished(self, matched_pages):
        self.main_window.pdf_path = self._pdf_path
        self.main_window.matched_pages = matched_pages
        self.progress.setMaximum(1)

        if matched_pages is None:
            # A cancellation (label dialog dismissed) unwinds scan_template()
            # via an exception before it ever returns. Nothing to hand off,
            # so Continue falls back to the same retry action as
            # change_file_button.
            self.status_label.setText("Scan cancelled.")
            self.progress.setValue(0)
            self.change_file_button.setText("Try Again")
            self.set_primary(enabled=True, callback=self.choose_pdf)
            return

        self.status_label.setText("Scan complete.")
        self.progress.setValue(1)
        self.set_primary(enabled=True, callback=self._on_continue)

    def _on_continue(self):
        self.main_window.sources_advisors_screen.show_form()
        self.main_window.stack.setCurrentWidget(self.main_window.sources_advisors_screen)

    def request_label(self, filename, pix_bytes):
        self.status_label.setText("New page found — needs a label…")

        dlg = LabelDialog(filename, pix_bytes)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.worker.receive_label(dlg.label())
        else:
            self.worker.receive_label(None)
