from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal
from gui.widgets.wizard_screen import WizardScreen
from pathlib import Path

ADVISOR_OPTIONS = [
    "Christie Whitney",
    "Dan Mavraides",
    "Kameron Javier",
    "Matt Jude",
    "Mitch Tuchman",
    "Sally Brandon",
    "Scott Puritz",
    "Sonja Breeding",
]

class SourcesAdvisorsScreen(WizardScreen):
    submitted = Signal(list, list) # sources [emx, bd], advisors [names]

    def __init__(self, main_window, settings):
        super().__init__("Sources & Advisors", "Choose this client's EMX and Black Diamond files, and the assigned advisors.")
        self.main_window = main_window
        self.settings = settings

        self._emx_path = None
        self._bd_path = None

        self.content_layout.addWidget(self._build_sources_section())
        self.content_layout.addWidget(self._build_advisors_section())

        self.set_primary("Continue", enabled=False, callback=self._on_continue)

        self._validate()

    def _build_sources_section(self):
        container = QVBoxLayout()
        container.setSpacing(8)

        section_label = QLabel("SOURCES")
        section_label.setProperty("class", "section")
        container.addWidget(section_label)

        self.emx_field, emx_row = self._build_source_row("EMX file", self._choose_emx)
        container.addLayout(emx_row)

        self.bd_field, bd_row = self._build_source_row("Black Diamond file", self._choose_bd)
        container.addLayout(bd_row)

        wrapper = self._wrap(container)
        return wrapper

    def _build_source_row(self, placeholder, on_browse):
        field = QLineEdit()
        field.setReadOnly(True)
        field.setPlaceholderText(f"No {placeholder.lower()} selected")

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
        container.setSpacing(8)

        section_label = QLabel("ADVISORS")
        section_label.setProperty("class", "section")
        container.addWidget(section_label)

        self.advisor_list = QListWidget()
        self.advisor_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.advisor_list.setFixedHeight(180)
        for advisor in ADVISOR_OPTIONS:
            item = QListWidgetItem(advisor)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.advisor_list.addItem(item)
        self.advisor_list.itemChanged.connect(lambda _: self._validate())
        container.addWidget(self.advisor_list)

        return self._wrap(container)

    def _wrap(self, layout):
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _choose_emx(self):
        filename = self._browse("EMX")
        if filename:
            self._emx_path = filename
            self.emx_field.setText(filename)
            self._validate()

    def _choose_bd(self):
        filename = self._browse("Black Diamond")
        if filename:
            self._bd_path = filename
            self.bd_field.setText(filename)
            self._validate()

    def _browse(self, label):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {label} PDF",
            self.settings.value("lastReplacementDir"),
            "PDF Files (*.pdf)"
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

    def _validate(self):
        ready = bool(self._emx_path) and bool(self._bd_path) and len(self._selected_advisors()) > 0
        self.set_primary(enabled=ready)

    def _on_continue(self):
        sources = [self._emx_path, self._bd_path]
        advisors = self._selected_advisors()
        self.submitted.emit(sources, advisors)

    def reset(self):
        self._emx_path = None
        self._bd_path = None
        self.emx_field.clear()
        self.bd_field.clear()
        for i in range(self.advisor_list.count()):
            self.advisor_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._validate()
