from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QProgressBar, QTextEdit, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path
import json
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.library_row import LibraryRow
from gui.workers.scan_worker import ScanWorker
from gui.dialogs.label_dialog import LabelDialog
from gui.dialogs.advisor_role_dialog import classify_advisors
from gui.theme import repolish
from src.paths import TEMPLATE_CONFIG_PATH
from src.scanner import save_template
from src.advisors import (
    ensure_advisors_split,
    load_cached_advisors,
    load_advisor_roles,
    unclassified_advisors,
)
from src.tear_sheets import ensure_tear_sheets_split, load_cached_tear_sheets

PDF_EXTENSIONS = {".pdf"}


class LibraryScreen(QWidget):
    """Everything that's set up once and reused for every report: the
    report template, the advisors roster and the tear sheets. Each is
    fingerprinted/split once and cached, and redone automatically only when
    the provided file changes. Which advisors apply to a particular report,
    and which tear sheets get inserted, is decided per report (see the
    Builder and assembler.py).

    The template scan starts as soon as this screen is created, whichever
    screen is showing, so a returning user finds it already done.
    """

    # "ok" | "warn" | "busy", plus a one-line description for a tooltip.
    status_changed = Signal(str, str)
    # Emitted when the template scan finishes: True if it produced pages.
    template_ready_changed = Signal(bool)
    # Advisors, roles or tear sheets changed -- the Builder re-reads them.
    contents_changed = Signal()
    # The user finished first-time setup (all three files provided) and
    # chose to continue to the report builder.
    setup_finished = Signal()

    def __init__(self, main_window, settings):
        super().__init__()
        self.main_window = main_window
        self.settings = settings
        self._pdf_path = ""
        self._scanning = False
        self._template_ok = False
        self._scan_cancelled = False
        self.thread = None
        self.worker = None

        # Until the template, advisors and tear sheets have all been
        # provided, the Library stays on screen and the builder out of
        # reach -- left to find them later, people never would.
        self._setup_pending = self._needs_setup()

        title = QLabel("Library")
        title.setProperty("class", "title")
        subtitle = QLabel("Set these up once. Ressemble reuses them for every report.")
        subtitle.setProperty("class", "subtitle")

        self.welcome_banner = QFrame()
        self.welcome_banner.setProperty("class", "banner")
        welcome_layout = QVBoxLayout()
        welcome_layout.setContentsMargins(14, 10, 14, 10)
        welcome_layout.setSpacing(2)
        welcome_title = QLabel("Welcome to Ressemble")
        welcome_title.setProperty("class", "row-title")
        welcome_text = QLabel(
            "Add your report template, advisors file and tear sheets to get started. "
            "Continue unlocks once all three are in. You can also drag each PDF onto its row."
        )
        welcome_text.setWordWrap(True)
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(welcome_text)
        self.welcome_banner.setLayout(welcome_layout)
        self.welcome_banner.setVisible(False)

        self.template_row = self._build_template_row()
        self.advisors_row = self._build_advisors_row()
        self.tear_sheets_row = self._build_tear_sheets_row()

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        layout.addWidget(self.welcome_banner)
        layout.addWidget(self.template_row)
        layout.addWidget(self.advisors_row)
        layout.addWidget(self.tear_sheets_row)
        layout.addStretch(1)
        layout.addWidget(self._build_setup_footer())
        self.setLayout(layout)

        self._start()

    # --- building the rows ---

    def _build_template_row(self):
        row = LibraryRow("template", "Report template", PDF_EXTENSIONS)
        row.file_dropped.connect(self._use_pdf)
        self.template_replace_button = row.add_button("Choose file", self.choose_pdf)
        self.rescan_button = row.add_button("Rescan", self.rescan_pdf)

        self.scan_status_label = QLabel("")
        self.scan_status_label.setProperty("class", "status")
        self.scan_progress = QProgressBar()
        self.scan_progress.setMinimum(0)
        self.scan_progress.setMaximum(0)

        self.scan_log = QTextEdit()
        self.scan_log.setReadOnly(True)
        self.scan_log.setFixedHeight(140)
        self.scan_details = CollapsibleSection("Details", self.scan_log, collapsed=True)

        self.scan_box = QWidget()
        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)
        box.addWidget(self.scan_status_label)
        box.addWidget(self.scan_progress)
        self.scan_box.setLayout(box)
        self.scan_box.setVisible(False)

        row.extra.addWidget(self.scan_box)
        row.extra.addWidget(self.scan_details)
        self.scan_details.setVisible(False)
        return row

    def _build_setup_footer(self):
        self.setup_reason = QLabel("")
        self.setup_reason.setProperty("class", "status")
        self.setup_reason.setWordWrap(True)

        self.setup_button = QPushButton("Continue")
        self.setup_button.setProperty("class", "primary")
        self.setup_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setup_button.clicked.connect(self._finish_setup)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self.setup_reason, 1)
        layout.addWidget(self.setup_button)

        self.setup_box = QWidget()
        self.setup_box.setLayout(layout)
        return self.setup_box

    def _build_advisors_row(self):
        row = LibraryRow("users", "Advisors", PDF_EXTENSIONS)
        row.file_dropped.connect(self._use_advisors_pdf)
        self.advisors_choose_button = row.add_button("Choose file", self.choose_advisors_pdf)
        # Re-walks every team member, not just unclassified ones, so a
        # wrong Advisor/Service pick can be corrected later.
        self.advisors_roles_button = row.add_button("Edit roles", self._edit_advisor_roles)
        return row

    def _build_tear_sheets_row(self):
        row = LibraryRow("chart-pie", "Tear sheets", PDF_EXTENSIONS)
        row.file_dropped.connect(self._use_tear_sheets_pdf)
        self.tear_choose_button = row.add_button("Choose file", self.choose_tear_sheets_pdf)
        return row

    # --- startup ---

    def _start(self):
        self._load_cached_advisors_display()
        self._load_cached_tear_sheets_display()

        filename = self._saved_template()
        if filename:
            self._pdf_path = filename
            self.scan_pdf()
        else:
            # First run -- nothing to scan until the user picks a template.
            self._refresh_template_row()
            self._emit_status()

    @staticmethod
    def _saved_template():
        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                return json.load(template_config).get("filename") or ""
        except (FileNotFoundError, json.JSONDecodeError):
            return ""

    def is_first_run(self):
        return not self._pdf_path

    def setup_pending(self):
        return self._setup_pending

    def _needs_setup(self):
        """True when any of the three files is missing at launch. That
        covers a first run and also a library that was cleared, so a user
        is never dropped into the builder with nothing to build from."""
        return not self._saved_template() or self._missing_for_setup() != []

    def _missing_for_setup(self):
        """What's still needed to finish setup, as short phrases."""
        missing = []
        if not self._template_ok and not self._saved_template():
            missing.append("a report template")

        _, names = load_cached_advisors()
        if not names:
            missing.append("an advisors file")

        _, models = load_cached_tear_sheets()
        if not models:
            missing.append("a tear sheets file")
        return missing

    def _finish_setup(self):
        self._setup_pending = False
        self._update_setup()
        self._refresh_template_row()
        self._set_tear_sheets_row(*load_cached_tear_sheets())
        self.setup_finished.emit()

    def _set_primary(self, button, primary):
        button.setProperty("class", "primary" if primary else "")
        repolish(button)

    def _update_setup(self):
        """Keeps the first-time-setup footer, welcome banner and the
        highlighted next step in step with what's been provided."""
        self.welcome_banner.setVisible(self._setup_pending)
        self.setup_box.setVisible(self._setup_pending)

        steps = (self.template_replace_button, self.advisors_choose_button, self.tear_choose_button)
        if not self._setup_pending:
            for button in steps + (self.advisors_roles_button,):
                self._set_primary(button, False)
            return

        _, names = load_cached_advisors()
        roles = load_advisor_roles()
        needs_roles = [name for name in names if name not in roles]
        _, models = load_cached_tear_sheets()

        template_missing = not self._template_ok and not self._scanning
        advisors_missing = not names
        tear_missing = not models

        # Primary goes to the next thing to do, never to two at once.
        next_button = None
        if template_missing:
            next_button = self.template_replace_button
        elif advisors_missing:
            next_button = self.advisors_choose_button
        elif needs_roles:
            next_button = self.advisors_roles_button
        elif tear_missing:
            next_button = self.tear_choose_button

        ready = next_button is None and not self._scanning
        for button in steps + (self.advisors_roles_button,):
            self._set_primary(button, button is next_button)

        missing = []
        if template_missing:
            missing.append("a report template")
        if advisors_missing:
            missing.append("an advisors file")
        if tear_missing:
            missing.append("a tear sheets file")

        if self._scanning:
            reason = "Scanning the template…"
        elif missing:
            reason = "Still needed: " + ", ".join(missing[:-1]) + (" and " if len(missing) > 1 else "") + missing[-1] + "."
        elif needs_roles:
            plural = "people" if len(needs_roles) != 1 else "person"
            reason = f"Set a role for {len(needs_roles)} {plural} to continue."
        else:
            reason = "Everything is in. You're ready to build reports."

        self.setup_reason.setText(reason)
        self.setup_button.setEnabled(ready)

    def template_ready(self):
        return self._template_ok and not self._scanning

    def scanning(self):
        return self._scanning

    # --- template ---

    def choose_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Report Template",
            self.settings.value("lastTemplateDir"),
            "PDF Files (*.pdf)"
        )

        if filename:
            self._use_pdf(filename)

    def _use_pdf(self, filename):
        self.settings.setValue("lastTemplateDir", str(Path(filename).parent))
        self._pdf_path = filename
        self.scan_pdf()

    def rescan_pdf(self):
        # Forces a real rescan of the current template -- bypassing the
        # "unchanged, reuse the cached scan" shortcut in scan_template().
        self.scan_pdf(refresh=True)

    def scan_pdf(self, refresh=False):
        if self._scanning:
            return

        self._scanning = True
        self._template_ok = False
        self._scan_cancelled = False
        self.scan_log.clear()
        self.scan_progress.setMaximum(0)
        self.scan_progress.setValue(0)
        self.scan_status_label.setText("Starting scan…")
        self.scan_box.setVisible(True)
        self.scan_details.setVisible(True)
        self._refresh_template_row()
        self._emit_status()
        self.template_ready_changed.emit(False)

        self.thread = QThread()
        self.worker = ScanWorker(pdf=self._pdf_path, refresh=refresh)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.scan_log.append)
        self.worker.progress.connect(self.on_progress)
        self.worker.request_label.connect(self.request_label)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.on_scan_finished)

        self.thread.start()

    def on_progress(self, current, total):
        self.scan_progress.setMaximum(total)
        self.scan_progress.setValue(current)
        self.scan_status_label.setText(f"Scanning page {current} of {total}…")

    def on_scan_finished(self, matched_pages):
        self._scanning = False
        self.main_window.pdf_path = self._pdf_path
        self.main_window.matched_pages = matched_pages
        self.scan_progress.setMaximum(1)

        if matched_pages is None:
            # A cancellation (label dialog dismissed) unwinds scan_template()
            # via an exception before it ever returns.
            self._scan_cancelled = True
            self._template_ok = False
            self.scan_status_label.setText("Scan cancelled.")
            self.scan_progress.setValue(0)
        else:
            self._persist_scanned_template(matched_pages)
            self._scan_cancelled = False
            self._template_ok = True
            self.scan_status_label.setText("Scan complete.")
            self.scan_progress.setValue(1)
            self.scan_box.setVisible(False)

        self._refresh_template_row()
        self._emit_status()
        self.template_ready_changed.emit(self._template_ok)

    def _persist_scanned_template(self, matched_pages):
        """Records the scanned template right away. Otherwise it would only
        be remembered once the first report was built, and closing the app
        after setup but before that would send the user back to choose it
        again."""
        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                config = json.load(template_config)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}

        if config.get("filename") == self._pdf_path and config.get("pages"):
            return
        save_template(self._pdf_path, matched_pages, config.get("sources") or {})

    def request_label(self, filename, pix_bytes):
        self.scan_status_label.setText("New page found. It needs a label…")

        dlg = LabelDialog(filename, pix_bytes)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.worker.receive_label(dlg.label())
        else:
            self.worker.receive_label(None)

    def _refresh_template_row(self):
        row = self.template_row
        self.template_replace_button.setText("Replace" if self._pdf_path else "Choose file")
        self.rescan_button.setVisible(bool(self._pdf_path))
        self.rescan_button.setEnabled(not self._scanning)
        self.template_replace_button.setEnabled(not self._scanning)

        row.set_file(self._pdf_path or "No template selected. Drag a PDF here or choose a file.")

        if self._scanning:
            row.chip.set_status("Scanning…", "busy")
            row.set_note("")
        elif self._template_ok:
            row.chip.set_status("Ready", "ok")
            pages = self._template_page_count()
            row.set_note(f"{pages} pages scanned" if pages else "")
        elif self._scan_cancelled:
            row.chip.set_status("Not scanned", "warn")
            row.set_note("The scan was cancelled. Rescan to try again.")
        else:
            row.chip.set_status("Not set", "warn")
            row.set_note("")

        self._update_setup()

    @staticmethod
    def _template_page_count():
        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                return len(json.load(template_config).get("pages") or [])
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    # --- advisors ---

    def _load_cached_advisors_display(self):
        cached_source, cached_names = load_cached_advisors()
        self._set_advisors_row(cached_source, cached_names)

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
        # Re-splitting is skipped internally if this is the same file as
        # last time, so it's safe to call unconditionally on every
        # selection/drop rather than tracking "did this actually change".
        try:
            names = ensure_advisors_split(filename)
        except Exception as exc:
            self.advisors_row.set_note(f"Couldn't read advisors from that file: {exc}")
            return

        # Only people never classified before -- roles persist by name
        # across sessions and across replacement team-pages files.
        classify_advisors(unclassified_advisors(names), self)
        self._set_advisors_row(filename, names)
        self.contents_changed.emit()

    def _edit_advisor_roles(self):
        source, names = load_cached_advisors()
        classify_advisors(names, self, current_roles=load_advisor_roles())
        self._set_advisors_row(source, names)
        self.contents_changed.emit()

    def _set_advisors_row(self, source, names):
        row = self.advisors_row
        self.advisors_roles_button.setEnabled(bool(names))
        row.set_file(source or "No advisors file selected. Drag a PDF here or choose a file.")

        if not names:
            row.chip.set_status("Not set" if not source else "None found", "warn")
            row.set_note("" if not source else "No advisors found in that file.")
        else:
            roles = load_advisor_roles()
            missing = [name for name in names if name not in roles]
            plural = "s" if len(names) != 1 else ""
            row.set_note(f"{len(names)} team member{plural} found")
            if missing:
                row.chip.set_status(f"{len(missing)} need{'s' if len(missing) == 1 else ''} a role", "warn")
            else:
                row.chip.set_status("Ready", "ok")

        self._emit_status()
        self._update_setup()

    # --- tear sheets ---

    def _load_cached_tear_sheets_display(self):
        cached_source, cached_models = load_cached_tear_sheets()
        self._set_tear_sheets_row(cached_source, cached_models)

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
        try:
            models = ensure_tear_sheets_split(filename)
        except Exception as exc:
            self.tear_sheets_row.set_note(f"Couldn't read tear sheets from that file: {exc}")
            return

        self._set_tear_sheets_row(filename, models)
        self.contents_changed.emit()

    def _set_tear_sheets_row(self, source, models):
        row = self.tear_sheets_row
        row.set_file(source or "No tear sheets file selected. Drag a PDF here or choose a file.")

        if models:
            plural = "s" if len(models) != 1 else ""
            row.chip.set_status("Ready", "ok")
            row.set_note(f"{len(models)} tear sheet{plural} found")
            row.note_label.setToolTip(", ".join(models))
        elif source:
            row.chip.set_status("None found", "warn")
            row.set_note("No tear sheets found in that file.")
        elif self._setup_pending:
            row.chip.set_status("Not set", "warn")
            row.set_note("")
        else:
            row.chip.set_status("Optional", "busy")
            row.set_note("Without tear sheets, accounts are listed without one.")

        self._update_setup()

    # --- overall status, shown on the header's Library button ---

    def _emit_status(self):
        if self._scanning:
            self.status_changed.emit("busy", "Scanning the report template…")
            return
        if not self._template_ok:
            self.status_changed.emit("warn", "The report template isn't ready. Open the Library.")
            return

        _, names = load_cached_advisors()
        if not names:
            self.status_changed.emit("warn", "No advisors file yet. Open the Library.")
            return

        roles = load_advisor_roles()
        missing = [name for name in names if name not in roles]
        if missing:
            plural = "people need" if len(missing) != 1 else "person needs"
            self.status_changed.emit("warn", f"{len(missing)} {plural} a role. Open the Library.")
            return

        self.status_changed.emit("ok", "Library is ready")

    def refresh_status(self):
        """Re-reads advisors/roles for the header dot -- the Builder can
        change roles without going through this screen."""
        self._load_cached_advisors_display()
        self._emit_status()
