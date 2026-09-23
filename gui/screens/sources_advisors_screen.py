from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QThread
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.file_drop_line_edit import FileDropLineEdit
from gui.widgets.collapsible import CollapsibleSection
from gui.workers.finish_sources_worker import FinishSourcesWorker
from src.advisors import load_cached_advisors, load_cached_advisor_combos, advisor_combo_file
from pathlib import Path
from itertools import zip_longest

EMX_EXTENSIONS = {".pdf", ".doc", ".docx"}
BD_EXTENSIONS = {".pdf"}

ADVISOR_ROLES = ["Advisor 1", "Advisor 2", "Advisor 3", "Service Advisor"]

NO_COMBO_WARNING = "This combination doesn't match an existing team page -- the report will fall back to a placeholder for it."

class SourcesAdvisorsScreen(WizardScreen):
    """The per-report inputs left once the Scan screen has the template
    and advisors roster settled: this client's EMX and Black Diamond
    files, and which of the available advisors are on this report.
    Submitting swaps to an inline processing state (ordering the sources,
    persisting the advisor combination) and goes straight to Details when
    done -- it never bounces back through the Scan screen.

    Both source files are optional, independently of each other: not every
    meeting includes a financial plan update or a performance review, and
    a report can be run with neither. Leaving one out drops that whole
    section from the assembled report rather than leaving its placeholder
    pages in -- see SECTION_SLOTS in src/assembler.py. Only the advisor
    selection is actually required to continue.
    """

    def __init__(self, main_window, settings):
        super().__init__("Sources & Advisors", "Choose the assigned advisors, plus this client's EMX and Black Diamond files if the report includes them.")
        self.main_window = main_window
        self.settings = settings

        self._emx_path = None
        self._bd_path = None
        self.worker = None
        self.thread = None

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

        self.emx_field, emx_row = self._build_source_row(
            "EMX file", EMX_EXTENSIONS, self._choose_emx, self._clear_emx
        )
        self.emx_field.file_dropped.connect(self._set_emx)
        container.addLayout(emx_row)

        self.bd_field, bd_row = self._build_source_row(
            "Black Diamond file", BD_EXTENSIONS, self._choose_bd, self._clear_bd
        )
        self.bd_field.file_dropped.connect(self._set_bd)
        container.addLayout(bd_row)

        # Both files are optional, which isn't obvious from two empty
        # fields sitting above a Continue button that's already enabled.
        hint = QLabel(
            "Both files are optional — leave one out and that section is omitted from the report entirely."
        )
        hint.setProperty("class", "status")
        hint.setWordWrap(True)
        container.addWidget(hint)

        widget = QWidget()
        widget.setLayout(container)
        return widget

    def _build_source_row(self, placeholder, extensions, on_browse, on_clear):
        field = FileDropLineEdit(extensions)
        field.setReadOnly(True)
        field.setPlaceholderText(f"No {placeholder.lower()} selected (optional) -- drag a file here or browse")

        browse = QPushButton("Browse…")
        browse.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        browse.clicked.connect(on_browse)

        # The field is read-only, so without this a file picked by mistake
        # couldn't be taken back out -- which matters now that running
        # with no EMX/BD file at all is a legitimate choice rather than
        # just an unfinished form.
        clear = QPushButton("Clear")
        clear.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        clear.setVisible(False)
        clear.clicked.connect(on_clear)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(field, 1)
        row.addWidget(browse)
        row.addWidget(clear)

        field.clear_button = clear
        return field, row

    def _build_advisors_section(self):
        container = QVBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(8)

        section_label = QLabel("ADVISORS")
        section_label.setProperty("class", "section")
        container.addWidget(section_label)

        # Shown instead of the (empty) dropdowns when no advisors PDF has
        # been scanned yet -- there's no fixed roster shipped with the
        # app, see ScanScreen's advisors field / src/advisors.py.
        self.no_advisors_label = QLabel(
            "No advisors available -- provide an advisors PDF on the previous screen."
        )
        self.no_advisors_label.setProperty("class", "status")
        self.no_advisors_label.setWordWrap(True)
        self.no_advisors_label.setVisible(False)
        container.addWidget(self.no_advisors_label)

        # Optional shortcut: pick a whole known team at once instead of
        # setting each of the four roles by hand. Selecting an entry just
        # fills the role dropdowns below with that team's names (in
        # whatever order load_cached_advisor_combos() -- ultimately
        # split_advisors_pdf() -- found them in) and immediately resets
        # itself back to blank, since it's a one-shot fill rather than a
        # selection that needs to stay in sync with hand-edits made
        # afterward.
        quick_select_row = QHBoxLayout()
        quick_select_row.setSpacing(8)

        quick_select_label = QLabel("Team Page")
        quick_select_label.setFixedWidth(110)
        quick_select_row.addWidget(quick_select_label)

        self.quick_select_combo = QComboBox()
        self.quick_select_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.quick_select_combo.currentIndexChanged.connect(self._on_quick_select_changed)
        quick_select_row.addWidget(self.quick_select_combo, 1)

        self.quick_select_row_widget = QWidget()
        self.quick_select_row_widget.setLayout(quick_select_row)
        container.addWidget(self.quick_select_row_widget)

        # Four independent role slots rather than a multi-select list --
        # picking a team is really "who's in each of these roles", and a
        # combo file is just whichever set of names that produces (see
        # advisor_combo_file() in src/advisors.py, which dedupes/sorts
        # before matching, so which slot a name lands in -- or the same
        # name landing in two slots -- doesn't matter to the lookup
        # itself). Nothing here prevents an unmatched combination from
        # being picked; _update_combo_warning() below only ever warns.
        self.advisor_combos = []
        self.advisor_rows = []
        advisors_grid = QVBoxLayout()
        advisors_grid.setSpacing(8)
        for role in ADVISOR_ROLES:
            row = QHBoxLayout()
            row.setSpacing(8)

            label = QLabel(role)
            label.setFixedWidth(110)
            row.addWidget(label)

            combo = QComboBox()
            combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            combo.currentIndexChanged.connect(self._on_advisor_combo_changed)
            row.addWidget(combo, 1)

            row_widget = QWidget()
            row_widget.setLayout(row)

            self.advisor_combos.append(combo)
            self.advisor_rows.append(row_widget)
            advisors_grid.addWidget(row_widget)

        container.addLayout(advisors_grid)

        self.advisor_warning_label = QLabel(NO_COMBO_WARNING)
        self.advisor_warning_label.setProperty("class", "warning")
        self.advisor_warning_label.setWordWrap(True)
        self.advisor_warning_label.setVisible(False)
        container.addWidget(self.advisor_warning_label)

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
        previous = self._advisor_slot_values() if preserve_selection else [""] * len(self.advisor_combos)
        _, names = load_cached_advisors()
        self._populate_advisors(names, previous)

    def _populate_advisors(self, names, previous):
        for combo, prior_value in zip(self.advisor_combos, previous):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("", "")
            for name in names:
                combo.addItem(name, name)

            index = combo.findData(prior_value) if prior_value else 0
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

        # Filtered to what actually fits the role dropdowns below -- a
        # team page with more members than there are roles (not the case
        # in any real data seen so far, but not guaranteed by anything)
        # couldn't be fully applied by _on_quick_select_changed() anyway,
        # so it's left out rather than offered and silently truncated.
        combos = [c for c in load_cached_advisor_combos() if len(c) <= len(self.advisor_combos)]
        self.quick_select_combo.blockSignals(True)
        self.quick_select_combo.clear()
        self.quick_select_combo.addItem("", None)
        for combo_names in combos:
            self.quick_select_combo.addItem(", ".join(combo_names), combo_names)
        self.quick_select_combo.setCurrentIndex(0)
        self.quick_select_combo.blockSignals(False)

        self.no_advisors_label.setVisible(not names)
        self.quick_select_row_widget.setVisible(bool(combos))
        for row_widget in self.advisor_rows:
            row_widget.setVisible(bool(names))

        self._update_combo_warning()

    def _on_quick_select_changed(self):
        combo_names = self.quick_select_combo.currentData()

        if combo_names:
            for role_combo, name in zip_longest(self.advisor_combos, combo_names, fillvalue=""):
                role_combo.blockSignals(True)
                index = role_combo.findData(name) if name else 0
                role_combo.setCurrentIndex(index if index >= 0 else 0)
                role_combo.blockSignals(False)

            # One-shot fill -- reset immediately rather than leaving this
            # showing a team name that a subsequent hand-edit to one of
            # the role dropdowns would silently make inaccurate.
            self.quick_select_combo.blockSignals(True)
            self.quick_select_combo.setCurrentIndex(0)
            self.quick_select_combo.blockSignals(False)

        self._update_combo_warning()
        self._validate()

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
        self._emx_path = filename or None
        self.emx_field.setText(filename or "")
        self.emx_field.clear_button.setVisible(bool(filename))
        self._validate()

    def _set_bd(self, filename):
        self._bd_path = filename or None
        self.bd_field.setText(filename or "")
        self.bd_field.clear_button.setVisible(bool(filename))
        self._validate()

    def _clear_emx(self):
        self._set_emx(None)

    def _clear_bd(self):
        self._set_bd(None)

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

    def _advisor_slot_values(self):
        """One entry per dropdown, in role order (Advisor 1/2/3, Service
        Advisor) -- "" for a slot left on the blank placeholder. Duplicate
        names across slots are kept as-is; deduplication happens in
        advisor_combo_file(), not here."""
        return [combo.currentData() or "" for combo in self.advisor_combos]

    def _selected_advisors(self):
        return [name for name in self._advisor_slot_values() if name]

    def _on_advisor_combo_changed(self):
        self._update_combo_warning()
        self._validate()

    def _update_combo_warning(self):
        # Purely informational -- see the class docstring's note on this
        # screen not restricting the combination, just flagging one that
        # won't have a real page to insert at report time.
        selected = self._selected_advisors()
        has_match = bool(selected) and advisor_combo_file(selected) is not None
        self.advisor_warning_label.setVisible(bool(selected) and not has_match)

    def _validate(self):
        # The EMX and BD files are deliberately not part of this -- a
        # report with neither is a valid report (see the class docstring).
        ready = len(self._selected_advisors()) > 0
        self.set_primary(enabled=ready)

    def show_form(self, preserve_selection=True):
        self._refresh_advisors(preserve_selection=preserve_selection)
        self.form_widget.setVisible(True)
        self.processing_widget.setVisible(False)
        self.set_title("Sources & Advisors")
        self.set_subtitle("Choose the assigned advisors, plus this client's EMX and Black Diamond files if the report includes them.")
        self.set_primary("Continue", callback=self._on_continue, visible=True)
        # Explicit callback (not just visible=True) so this always wins
        # back over _cancel_processing -- _show_processing() repoints
        # Back at that while a worker's running, and set_back() only
        # reconnects when given a callback, not merely toggled visible.
        self.back_button.setText("Back")
        self.set_back(callback=self._on_back, visible=True)
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

        # There's still no way to actually cancel a running
        # FinishSourcesWorker (Qt threads can't be safely force-stopped),
        # but leaving Back/Cancel hidden the whole time this runs meant a
        # slow or stuck step left the user with no way out of the screen
        # at all. Cancel below detaches this screen from the worker and
        # returns to the form; the worker itself keeps running to
        # completion in the background rather than being killed.
        self.back_button.setText("Cancel")
        self.set_back(callback=self._cancel_processing, visible=True)

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
        self.worker.progress.connect(self.on_progress)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self._on_finished)

        self.thread.start()

    def _cancel_processing(self):
        # Detaches this screen from the still-running worker so a
        # log/progress/finished signal that arrives after this point
        # can't touch UI the user has already navigated away from.
        # thread.quit()/deleteLater() stay connected (not disconnected
        # here), so the abandoned thread still cleans itself up normally
        # once finish_sources() returns instead of being leaked.
        if self.worker is not None:
            self.worker.log.disconnect(self.log.append)
            self.worker.progress.disconnect(self.on_progress)
            self.worker.finished.disconnect(self._on_finished)

        self.show_form(preserve_selection=True)

    def on_progress(self, current, total):
        # Stays indeterminate (see _show_processing()) until the first
        # real progress report arrives -- EMX/BD ordering runs as two
        # separate stages (see get_emx_order()/get_bd_order() in
        # scanner.py), each restarting its own current/total from 1, so
        # this can jump backward once when the second stage begins; the
        # log lines around each call already announce that transition.
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_finished(self, sources):
        if sources is None:
            self.status_label.setText("Something went wrong — check details below.")
            # Back was repointed at _cancel_processing (and relabeled
            # "Cancel") for the duration of the run -- point it back at
            # the normal handler now that the worker's actually done,
            # same as show_form() does; otherwise a click here would try
            # to disconnect signals on a worker Qt's about to delete.
            self.back_button.setText("Back")
            self.set_back(callback=self._on_back, visible=True)
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
        self._clear_emx()
        self._clear_bd()
        self.show_form(preserve_selection=False)
