from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QThread
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.file_drop_line_edit import FileDropLineEdit
from gui.widgets.checkable_list_widget import CheckableListWidget
from gui.widgets.collapsible import CollapsibleSection
from gui.workers.finish_sources_worker import FinishSourcesWorker
from src.advisors import load_cached_advisors, advisor_combo_file
from pathlib import Path

EMX_EXTENSIONS = {".pdf", ".doc", ".docx"}
BD_EXTENSIONS = {".pdf"}

NO_COMBO_TOOLTIP = "This Advisor combination page has not been provided"

class SourcesAdvisorsScreen(WizardScreen):
    """The per-report inputs left once the Scan screen has the template
    and advisors roster settled: this client's EMX and Black Diamond
    files, and which of the available advisors are on this report.
    Submitting swaps to an inline processing state (ordering the sources,
    persisting the advisor combination) and goes straight to Details when
    done -- it never bounces back through the Scan screen.
    """

    def __init__(self, main_window, settings):
        super().__init__("Sources & Advisors", "Choose this client's EMX and Black Diamond files, and the assigned advisors.")
        self.main_window = main_window
        self.settings = settings

        self._emx_path = None
        self._bd_path = None

        self.form_widget = self._build_form()
        self.processing_widget = self._build_processing()
        self.content_layout.addWidget(self.form_widget)
        self.content_layout.addWidget(self.processing_widget)

        self.set_back(callback=self._on_back)

        self.show_form()

    def _build_form(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        outer.addWidget(self._build_sources_section())
        outer.addWidget(self._build_advisors_section())

        widget = QWidget()
        widget.setLayout(outer)
        return widget

    def _build_sources_section(self):
        container = QVBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(8)

        section_label = QLabel("SOURCES")
        section_label.setProperty("class", "section")
        container.addWidget(section_label)

        self.emx_field, emx_row = self._build_source_row("EMX file", EMX_EXTENSIONS, self._choose_emx)
        self.emx_field.file_dropped.connect(self._set_emx)
        container.addLayout(emx_row)

        self.bd_field, bd_row = self._build_source_row("Black Diamond file", BD_EXTENSIONS, self._choose_bd)
        self.bd_field.file_dropped.connect(self._set_bd)
        container.addLayout(bd_row)

        widget = QWidget()
        widget.setLayout(container)
        return widget

    def _build_source_row(self, placeholder, extensions, on_browse):
        field = FileDropLineEdit(extensions)
        field.setReadOnly(True)
        field.setPlaceholderText(f"No {placeholder.lower()} selected -- drag a file here or browse")

        browse = QPushButton("Browse…")
        browse.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        browse.clicked.connect(on_browse)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(field, 1)
        row.addWidget(browse)
        return field, row

    def _build_advisors_section(self):
        container = QVBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(8)

        section_label = QLabel("ADVISORS")
        section_label.setProperty("class", "section")
        container.addWidget(section_label)

        # Shown instead of the (empty) list when no advisors PDF has been
        # scanned yet -- there's no fixed roster shipped with the app, see
        # ScanScreen's advisors field / src/advisors.py.
        self.no_advisors_label = QLabel(
            "No advisors available -- provide an advisors PDF on the previous screen."
        )
        self.no_advisors_label.setProperty("class", "status")
        self.no_advisors_label.setWordWrap(True)
        self.no_advisors_label.setVisible(False)
        container.addWidget(self.no_advisors_label)

        self.advisor_list = CheckableListWidget()
        self.advisor_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.advisor_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.advisor_list.itemChanged.connect(self._on_advisor_item_changed)
        container.addWidget(self.advisor_list)

        widget = QWidget()
        widget.setLayout(container)
        return widget

    def _build_processing(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.status_label = QLabel("Processing sources…")
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

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _refresh_advisors(self, preserve_selection=True):
        checked = set(self._selected_advisors()) if preserve_selection else frozenset()
        _, names = load_cached_advisors()
        self._populate_advisors(names, checked=checked)

    def _populate_advisors(self, names, checked=frozenset()):
        self.advisor_list.blockSignals(True)
        self.advisor_list.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in checked else Qt.CheckState.Unchecked)
            self.advisor_list.addItem(item)
        self.advisor_list.blockSignals(False)

        self.no_advisors_label.setVisible(not names)
        self.advisor_list.setVisible(bool(names))

        if names:
            # QListWidget's sizeHint() is a fixed default, not
            # content-driven -- it doesn't grow with item count, it just
            # relies on its scrollbar for overflow. Pin the height to
            # exactly what all rows need instead.
            row_height = self.advisor_list.sizeHintForRow(0)
            frame = 2 * self.advisor_list.frameWidth()
            self.advisor_list.setFixedHeight(row_height * self.advisor_list.count() + frame)

        self._update_advisor_availability()

    def _choose_emx(self):
        # A .doc/.docx EMX source gets converted to PDF (and fully debolded)
        # once sources are handed off -- see
        # src/office_import.py:prepare_emx_source, called from
        # src/scanner.py:request_source_files.
        filename = self._browse("EMX", "EMX Files (*.pdf *.doc *.docx)")
        if filename:
            self._set_emx(filename)

    def _choose_bd(self):
        filename = self._browse("Black Diamond", "PDF Files (*.pdf)")
        if filename:
            self._set_bd(filename)

    def _set_emx(self, filename):
        self._emx_path = filename
        self.emx_field.setText(filename)
        self._validate()

    def _set_bd(self, filename):
        self._bd_path = filename
        self.bd_field.setText(filename)
        self._validate()

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

    def _selected_advisors(self):
        return [
            self.advisor_list.item(i).text()
            for i in range(self.advisor_list.count())
            if self.advisor_list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def _on_advisor_item_changed(self, item):
        self._update_advisor_availability()
        self._validate()

    def _update_advisor_availability(self):
        # Guides the user toward combinations that actually have a page
        # (see src/advisors.py) rather than letting them assemble an
        # arbitrary set that silently falls back to a placeholder at
        # report time. The first pick is always free -- there's no page
        # for a single advisor alone, so nothing would ever be selectable
        # if that were also constrained.
        checked = self._selected_advisors()

        # setFlags()/setToolTip() also emit itemChanged in this Qt version,
        # not just check-state edits -- without blocking, that re-enters
        # _on_advisor_item_changed -> here, infinitely.
        self.advisor_list.blockSignals(True)
        for i in range(self.advisor_list.count()):
            item = self.advisor_list.item(i)

            if item.checkState() == Qt.CheckState.Checked or not checked:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip("")
                continue

            if advisor_combo_file(checked + [item.text()]):
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip("")
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip(NO_COMBO_TOOLTIP)
        self.advisor_list.blockSignals(False)

    def _validate(self):
        ready = bool(self._emx_path) and bool(self._bd_path) and len(self._selected_advisors()) > 0
        self.set_primary(enabled=ready)

    def show_form(self, preserve_selection=True):
        self._refresh_advisors(preserve_selection=preserve_selection)
        self.form_widget.setVisible(True)
        self.processing_widget.setVisible(False)
        self.set_title("Sources & Advisors")
        self.set_subtitle("Choose this client's EMX and Black Diamond files, and the assigned advisors.")
        self.set_primary("Continue", callback=self._on_continue, visible=True)
        self.set_back(visible=True)
        self._validate()

    def _show_processing(self):
        self.form_widget.setVisible(False)
        self.processing_widget.setVisible(True)
        self.set_title("Processing Sources")
        self.set_subtitle("Ordering the EMX and Black Diamond pages for this report.")
        self.status_label.setText("Processing sources…")
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.log.clear()
        self.set_primary(visible=False)
        self.set_back(visible=False)

    def _on_continue(self):
        selected_advisors = self._selected_advisors()
        self._show_processing()

        self.thread = QThread()

        self.worker = FinishSourcesWorker(
            pdf=self.main_window.pdf_path,
            matched_pages=self.main_window.matched_pages,
            emx_pdf=self._emx_path,
            blackdiamond_pdf=self._bd_path,
            selected_advisors=selected_advisors,
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self._on_finished)

        self.thread.start()

    def _on_finished(self, sources):
        if sources is None:
            self.status_label.setText("Something went wrong — check details below.")
            self.set_back(visible=True)
            self.set_primary(text="Try Again", enabled=True, callback=self.show_form, visible=True)
            return

        self.main_window.scan_results = {
            "matched_pages": self.main_window.matched_pages,
            "sources": sources,
            "advisors_file": None,
        }
        self.main_window.stack.setCurrentWidget(self.main_window.details_screen)

    def _on_back(self):
        self.main_window.stack.setCurrentWidget(self.main_window.scan_screen)

    def reset(self):
        self._emx_path = None
        self._bd_path = None
        self.emx_field.clear()
        self.bd_field.clear()
        self.show_form(preserve_selection=False)
