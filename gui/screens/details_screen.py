from PySide6.QtWidgets import QLabel, QLineEdit, QCheckBox, QDateEdit, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QDate
from gui.widgets.wizard_screen import WizardScreen
from src.assembler import next_monday

class DetailsScreen(WizardScreen):
    def __init__(self, main_window, settings):
        super().__init__("Report Details", "A few last details before the report is compiled.")
        self.main_window = main_window
        self.settings = settings

        self.content_layout.addWidget(self._build_client_name())
        self.content_layout.addWidget(self._build_target_date())
        self.content_layout.addWidget(self._build_enrolled())
        self.content_layout.addWidget(self._build_page_numbers())

        self.set_primary("Compile Report", enabled=False, callback=self._on_continue)

        self.client_name_field.textChanged.connect(self._validate)
        self._validate()

    def _build_client_name(self):
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("CLIENT NAME")
        label.setProperty("class", "section")
        layout.addWidget(label)

        self.client_name_field = QLineEdit()
        self.client_name_field.setPlaceholderText("e.g. Johnson")
        layout.addWidget(self.client_name_field)

        widget.setLayout(layout)
        return widget

    def _build_target_date(self):
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("REPORT DATE")
        label.setProperty("class", "section")
        layout.addWidget(label)

        self.use_target_date = QCheckBox("Use a specific date instead of next Monday")
        self.use_target_date.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.use_target_date.toggled.connect(self._on_target_date_toggled)
        layout.addWidget(self.use_target_date)

        self.target_date_field = QDateEdit()
        self.target_date_field.setCalendarPopup(False)
        self.target_date_field.setDisplayFormat("MMMM d, yyyy")
        self.target_date_field.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.target_date_field.setEnabled(False)
        layout.addWidget(self.target_date_field)

        widget.setLayout(layout)
        return widget

    def _build_enrolled(self):
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("VIEW360")
        label.setProperty("class", "section")
        layout.addWidget(label)

        self.enrolled_checkbox = QCheckBox("Client is enrolled in View360")
        self.enrolled_checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.enrolled_checkbox)

        widget.setLayout(layout)
        return widget

    def _build_page_numbers(self):
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("PAGE NUMBERS")
        label.setProperty("class", "section")
        layout.addWidget(label)

        self.page_numbers_checkbox = QCheckBox("Automatically number pages")
        self.page_numbers_checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.page_numbers_checkbox.setChecked(True)
        layout.addWidget(self.page_numbers_checkbox)

        widget.setLayout(layout)
        return widget

    def _on_target_date_toggled(self, checked):
        self.target_date_field.setEnabled(checked)

    def _set_default_date(self):
        d = next_monday()
        self.target_date_field.setDate(QDate(d.year, d.month, d.day))

    def _validate(self):
        ready = bool(self.client_name_field.text().strip())
        self.set_primary(enabled=ready)

    def _on_continue(self):
        self.main_window.client_name = self.client_name_field.text().strip()
        self.main_window.enrolled = self.enrolled_checkbox.isChecked()
        self.main_window.include_page_numbers = self.page_numbers_checkbox.isChecked()

        if self.use_target_date.isChecked():
            self.main_window.target_date = self.target_date_field.date().toPython()
        else:
            self.main_window.target_date = None

        self.main_window.stack.setCurrentWidget(self.main_window.compile_screen)
        self.main_window.compile_screen.start()

    def reset(self):
        self.client_name_field.clear()
        self.use_target_date.setChecked(False)
        self.enrolled_checkbox.setChecked(False)
        self.page_numbers_checkbox.setChecked(True)
        self._set_default_date()

    def showEvent(self, event):
        super().showEvent(event)
        self._set_default_date()
        self.client_name_field.setFocus()
