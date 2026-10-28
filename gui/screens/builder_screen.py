from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QAbstractItemView,
    QScrollArea,
    QStackedWidget,
    QFileDialog,
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
)
from PySide6.QtCore import Qt, QDate, QEvent, Signal
from pathlib import Path
import json
import pymupdf
from gui.build_runner import BuildRunner, BuildParams
from gui.report_contents import describe_contents
from gui.dialogs.advisor_role_dialog import classify_advisors
from gui.widgets.section_card import SectionCard
from gui.widgets.segmented_control import SegmentedControl
from gui.widgets.file_source_row import FileSourceRow
from gui.widgets.team_picker import TeamPicker
from gui.widgets.options_card import OptionsCard
from gui.widgets.date_field import DateField
from gui.widgets.fit import FitScrollArea
from gui.widgets.summary_panel import SummaryPanel
from gui.widgets.build_view import BuildView
from gui.widgets.done_view import DoneView
from src.advisors import load_cached_advisors, load_advisor_roles, advisor_combo_file
from src.paths import TEMPLATE_CONFIG_PATH
from src.assembler import next_monday, format_report_date

EMX_EXTENSIONS = {".pdf"}
BD_EXTENSIONS = {".pdf"}

VIEW_FORM = 0
VIEW_BUILDING = 1
VIEW_DONE = 2


class BuilderScreen(QWidget):
    """Where a report gets made: the client, the source files and the team
    on one page, with a live "Report contents" panel beside them and a
    single Build button. Building and the finished report replace the form
    in place, so nothing here ever navigates to another page."""

    # Fired when the roles/advisors changed from here (Edit roles), so the
    # header's Library status can be re-read.
    library_changed = Signal()

    def __init__(self, main_window, settings):
        super().__init__()
        self.main_window = main_window
        self.settings = settings

        self._emx_path = None
        self._bd_path = None
        self._emx_pages = None
        self._bd_pages = None
        self._template_scanning = False
        self._template_ready = False
        self._disclaimer_pdf = None
        self._team_page_counts = {}

        self.runner = BuildRunner(self)
        self.runner.status.connect(self._on_status)
        self.runner.progress.connect(self._on_progress)
        self.runner.log.connect(self._on_log)
        self.runner.stalled.connect(self._on_stalled)
        self.runner.resumed.connect(self._on_resumed)
        self.runner.finished.connect(self._on_build_finished)

        self.form_view = self._build_form()
        self.build_view = BuildView()
        self.done_view = DoneView()

        self.build_view.retry_clicked.connect(self._on_retry)
        self.build_view.keep_waiting_clicked.connect(self._on_keep_waiting)
        self.build_view.edit_clicked.connect(self._show_form)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.form_view)
        self.stack.addWidget(self.build_view)
        self.stack.addWidget(self.done_view)

        self.summary = SummaryPanel()
        self.summary.setFixedWidth(250)
        self.summary.action_clicked.connect(self._on_action)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(20)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.summary)
        self.setLayout(layout)

        self._set_default_date()
        self.team_picker.refresh()
        self._refresh()

    # --- form ---

    def _build_form(self):
        page = QWidget()
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 12, 0)
        column.setSpacing(14)

        self.client_card = SectionCard(1, "Client")
        self._build_client(self.client_card)
        column.addWidget(self.client_card)

        self.files_card = SectionCard(2, "Source files", "optional")
        self._build_files(self.files_card)
        column.addWidget(self.files_card)

        self.team_card = SectionCard(3, "Team")
        self.team_picker = TeamPicker()
        self.team_picker.changed.connect(self._refresh)
        self.team_picker.edit_roles_requested.connect(self._edit_roles)
        self.team_card.body.addWidget(self.team_picker)
        column.addWidget(self.team_card)

        self.options_card = OptionsCard(self.settings)
        self.options_card.changed.connect(self._refresh)
        column.addWidget(self.options_card)

        column.addStretch(1)
        page.setLayout(column)

        scroll = FitScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _build_client(self, card):
        name_label = QLabel("Client name")
        name_label.setProperty("class", "field-label")
        self.client_name_field = QLineEdit()
        self.client_name_field.setPlaceholderText("Johnson")
        self.client_name_field.textChanged.connect(self._refresh)

        date_label = QLabel("Report date")
        date_label.setProperty("class", "field-label")
        self.date_mode = SegmentedControl(["Next Monday", "Pick a date"])
        self.date_mode.current_changed.connect(self._on_date_mode_changed)

        self.date_field = DateField()
        self.date_field.setVisible(False)
        self.date_field.dateChanged.connect(self._refresh)

        self.date_caption = QLabel("")
        self.date_caption.setProperty("class", "status")

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        grid.addWidget(name_label, 0, 0)
        grid.addWidget(self.client_name_field, 1, 0)
        grid.addWidget(date_label, 0, 1)
        grid.addWidget(self.date_mode, 1, 1, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self.date_field, 2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        card.body.addLayout(grid)
        card.body.addWidget(self.date_caption)

    def _build_files(self, card):
        self.emx_row = FileSourceRow("Financial plan (EMX)", EMX_EXTENSIONS, "Drop a PDF here")
        self.emx_row.browse_clicked.connect(self._choose_emx)
        self.emx_row.file_dropped.connect(self._set_emx)
        self.emx_row.cleared.connect(lambda: self._set_emx(None))

        self.bd_row = FileSourceRow("Portfolio (Black Diamond)", BD_EXTENSIONS, "Drop a PDF here")
        self.bd_row.browse_clicked.connect(self._choose_bd)
        self.bd_row.file_dropped.connect(self._set_bd)
        self.bd_row.cleared.connect(lambda: self._set_bd(None))

        hint = QLabel("Both are optional. Leave one out and that section is left out of the report.")
        hint.setProperty("class", "status")
        hint.setWordWrap(True)

        card.body.addWidget(self.emx_row)
        card.body.addWidget(self.bd_row)
        card.body.addWidget(hint)

    # --- dates ---

    def _set_default_date(self):
        d = next_monday()
        self.date_field.setDate(QDate(d.year, d.month, d.day))

    def _on_date_mode_changed(self, index):
        self.date_field.setVisible(index == 1)
        self._refresh()

    def _report_date(self):
        if self.date_mode.current_index() == 1:
            return self.date_field.date().toPython()
        return next_monday()

    # --- files ---

    def _choose_emx(self):
        filename = self._browse("EMX", "PDF Files (*.pdf)")
        if filename:
            self._set_emx(filename)

    def _choose_bd(self):
        filename = self._browse("Black Diamond", "PDF Files (*.pdf)")
        if filename:
            self._set_bd(filename)

    def _browse(self, label, file_filter):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {label} File",
            self.settings.value("lastReplacementDir"),
            file_filter
        )
        if filename:
            self.settings.setValue("lastReplacementDir", str(Path(filename).parent))
        return filename

    def _set_emx(self, path):
        self._emx_path = path or None
        self._emx_pages = self._count_pages(path)
        self.emx_row.set_path(path)
        self._refresh()

    def _set_bd(self, path):
        self._bd_path = path or None
        self._bd_pages = self._count_pages(path)
        self.bd_row.set_path(path)
        self._refresh()

    @staticmethod
    def _count_pages(path):
        """Page count for a PDF, or None if there's no file or it can't be read."""
        if not path:
            return None
        try:
            with pymupdf.open(path) as doc:
                return doc.page_count
        except Exception:
            return None

    @staticmethod
    def _source_detail(path, pages):
        if not path:
            return None
        name = Path(path).name
        if pages:
            plural = "s" if pages != 1 else ""
            return f"{pages} page{plural} · {name}"
        return name

    # --- team ---

    def _edit_roles(self):
        source, names = load_cached_advisors()
        classify_advisors(names, self, current_roles=load_advisor_roles())
        self.team_picker.refresh(preserve_selection=True)
        self.library_changed.emit()
        self._refresh()

    def _single_page_team_pdf(self, advisors):
        """The team file for these advisors if it's a single page -- only
        then is there one page to preview -- else None."""
        path = advisor_combo_file(advisors)
        if path is None:
            return None

        try:
            key = (str(path), path.stat().st_mtime)
        except OSError:
            return None
        if key not in self._team_page_counts:
            self._team_page_counts[key] = self._count_pages(str(path))
        return str(path) if self._team_page_counts[key] == 1 else None

    def _load_disclaimer_pdf(self):
        """The template's Plan 360 disclaimer page, which is all that's
        left of the Plan 360 section when there's no EMX file."""
        self._disclaimer_pdf = None
        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                pages = json.load(template_config).get("pages") or []
        except (FileNotFoundError, json.JSONDecodeError):
            return

        for page in pages:
            if page.get("slot") == "plan360Disclaimer" and Path(page.get("filename", "")).exists():
                self._disclaimer_pdf = page["filename"]
                return

    # --- library state, pushed in by MainWindow ---

    def set_template_state(self, scanning, ready):
        self._template_scanning = scanning
        self._template_ready = ready
        self._load_disclaimer_pdf()
        self._refresh()

    # --- live summary ---

    def _refresh(self, *_):
        name = self.client_name_field.text().strip()
        advisors = self.team_picker.selected_advisors()
        date = self._report_date()

        self.date_caption.setText(f"Cover date: {format_report_date(date)}")

        self.client_card.set_done(bool(name))
        self.files_card.set_done(bool(self._emx_path or self._bd_path))
        self.team_card.set_done(bool(advisors))

        self.summary.set_rows(describe_contents(
            emx_pdf=self._emx_path,
            emx_pages=self._emx_pages,
            disclaimer_pdf=self._disclaimer_pdf,
            team_pdf=self._single_page_team_pdf(advisors),
            client_name=name,
            date_text=format_report_date(date),
            has_emx=bool(self._emx_path),
            has_bd=bool(self._bd_path),
            include_plan_360=self.options_card.plan_360.isChecked(),
            team_names=advisors,
            emx_detail=self._source_detail(self._emx_path, self._emx_pages),
            bd_detail=self._source_detail(self._bd_path, self._bd_pages),
        ))

        if self.stack.currentIndex() != VIEW_FORM:
            return

        if self._template_scanning:
            self.summary.set_state(False, "Scanning the template…")
        elif not self._template_ready:
            self.summary.set_state(False, "Set up the report template in the Library.")
        elif not name:
            self.summary.set_state(False, "Enter a client name to build.")
        elif not advisors:
            self.summary.set_state(False, "Choose at least one advisor.")
        else:
            self.summary.set_state(True, "Ready to build", ready=True)

    # --- building ---

    def _on_action(self):
        if self.stack.currentIndex() == VIEW_DONE:
            self.main_window.restart()
        elif self.runner.is_running():
            self.runner.cancel()
        else:
            self._on_build()

    def _on_build(self):
        date = self._report_date()
        params = BuildParams(
            pdf=self.main_window.pdf_path,
            matched_pages=self.main_window.matched_pages,
            emx_pdf=self._emx_path,
            blackdiamond_pdf=self._bd_path,
            advisors=self.team_picker.selected_advisors(),
            client_name=self.client_name_field.text().strip(),
            enrolled=self.options_card.enrolled.isChecked(),
            # None lets the assembler use next Monday itself, as before.
            target_date=date if self.date_mode.current_index() == 1 else None,
            include_page_numbers=self.options_card.page_numbers.isChecked(),
            include_plan_360=self.options_card.plan_360.isChecked(),
        )

        self.build_view.reset(params.client_name)
        self.stack.setCurrentIndex(VIEW_BUILDING)
        self.summary.set_action("cancel")
        self.runner.start(params)

    def _on_retry(self):
        self.build_view.reset(self.client_name_field.text().strip())
        self.summary.set_action("cancel")
        self.runner.retry()

    def _on_keep_waiting(self):
        self.build_view.set_stalled(False)
        self.runner.acknowledge_stall()

    def _on_status(self, text):
        self.build_view.set_status(text)

    def _on_progress(self, current, total):
        self.build_view.set_progress(current, total)

    def _on_log(self, text):
        self.build_view.append_log(text)

    def _on_stalled(self):
        self.build_view.set_stalled(True)

    def _on_resumed(self):
        self.build_view.set_stalled(False)

    def _on_build_finished(self, report_path, outcome):
        if outcome == "done":
            self.done_view.set_report(report_path)
            self.stack.setCurrentIndex(VIEW_DONE)
            self.summary.set_action("new")
            return

        message = "Building cancelled." if outcome == "cancelled" else "Something went wrong. Check the details below, then try again."
        self.build_view.show_failed(message)
        self.summary.set_action("rebuild")

    def _show_form(self):
        self.stack.setCurrentIndex(VIEW_FORM)
        self.summary.set_action("build")
        self._refresh()

    # --- lifecycle ---

    def reset(self):
        """Back to a blank form for the next report."""
        self.runner.stop()
        self.client_name_field.clear()
        self.date_mode.set_current_index(0)
        self.date_field.setVisible(False)
        self._set_default_date()
        self._emx_path = self._bd_path = None
        self._emx_pages = self._bd_pages = None
        self.emx_row.set_path(None)
        self.bd_row.set_path(None)
        self.team_picker.refresh(preserve_selection=False)
        self.options_card.reset()
        self.stack.setCurrentIndex(VIEW_FORM)
        self.summary.set_action("build")
        self._refresh()
        self.client_name_field.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        QApplication.instance().installEventFilter(self)
        # Roles or the advisors file may have changed in the Library.
        self.team_picker.refresh(preserve_selection=True)
        # Only refresh the default when it's actually in use -- otherwise a
        # chosen date would be silently overwritten when returning here.
        if self.date_mode.current_index() == 0:
            self._set_default_date()
        self._refresh()
        if self.stack.currentIndex() == VIEW_FORM and not self.client_name_field.text():
            self.client_name_field.setFocus()

    def hideEvent(self, event):
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        super().hideEvent(event)

    # Enter should build no matter which input has focus. QLineEdit and
    # friends accept the Return key themselves, so a plain keyPressEvent
    # override here would never see it -- an application-level filter
    # installed while this screen is visible intercepts it first.
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            focused = QApplication.focusWidget()
            if (
                self.stack.currentIndex() == VIEW_FORM
                and focused is not None
                and self.isAncestorOf(focused)
                and not isinstance(focused, (QPushButton, QComboBox, QAbstractItemView))
                and self.summary.build_button.isEnabled()
            ):
                self.summary.build_button.click()
                return True
        return super().eventFilter(watched, event)
