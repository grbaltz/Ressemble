from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from gui.icons import icon_label, icon
from gui.theme import MUTED_TEXT
from gui.widgets.toggle_switch import ToggleSwitch


class OptionsCard(QFrame):
    """The three report toggles, tucked into one line that summarizes them
    ("Plan 360 on · View360 off · ...") and expands in place to change them.
    Defaults are right for most reports, so they stay out of the way."""

    changed = Signal()

    # Remembered between reports, and between launches: a switch turned off
    # once stays off until it's turned back on. "Enrolled in View360" is
    # deliberately not remembered -- it describes one client, so carrying
    # it over would quietly put the wrong page in the next client's report.
    REMEMBERED = {"plan360": True, "pageNumbers": True}

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._settings = settings

        self.plan_360 = ToggleSwitch(self._remembered("plan360"))
        self.enrolled = ToggleSwitch(False)
        self.page_numbers = ToggleSwitch(self._remembered("pageNumbers"))
        self._switches = (self.plan_360, self.enrolled, self.page_numbers)
        for switch in self._switches:
            switch.toggled.connect(self._on_toggled)

        self.summary_label = QLabel()
        self.summary_label.setProperty("class", "status")

        self.toggle_button = QPushButton("Change")
        self.toggle_button.setProperty("class", "link")
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggle_button.clicked.connect(self._toggle_body)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(icon_label("sliders", MUTED_TEXT, 16))
        header.addWidget(self.summary_label, 1)
        header.addWidget(self.toggle_button)

        self.body = QWidget()
        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_layout.setSpacing(0)
        for label, switch in (
            ("Include Plan 360", self.plan_360),
            ("Client is enrolled in View360", self.enrolled),
            ("Number the pages automatically", self.page_numbers),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 8, 0, 8)
            row.addWidget(QLabel(label), 1)
            row.addWidget(switch)
            body_layout.addLayout(row)
        self.body.setLayout(body_layout)
        self.body.setVisible(False)

        outer = QVBoxLayout()
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(4)
        outer.addLayout(header)
        outer.addWidget(self.body)
        self.setLayout(outer)

        self._update_summary()

    def _remembered(self, key):
        return self._settings.value(f"options/{key}", self.REMEMBERED[key], type=bool)

    def _remember(self):
        self._settings.setValue("options/plan360", self.plan_360.isChecked())
        self._settings.setValue("options/pageNumbers", self.page_numbers.isChecked())
        # Written out now rather than at exit, so a crash can't lose it.
        self._settings.sync()

    def _toggle_body(self):
        expanded = not self.body.isHidden()
        self.body.setVisible(not expanded)
        self.toggle_button.setText("Change" if expanded else "Done")

    def _on_toggled(self):
        self._remember()
        self._update_summary()
        self.changed.emit()

    def _update_summary(self):
        on_off = lambda switch: "on" if switch.isChecked() else "off"
        self.summary_label.setText(
            f"Plan 360 {on_off(self.plan_360)} · View360 {on_off(self.enrolled)} · Page numbers {on_off(self.page_numbers)}"
        )

    def reset(self):
        # Back to what was last chosen, not the factory defaults.
        self.plan_360.setChecked(self._remembered("plan360"))
        self.enrolled.setChecked(False)
        self.page_numbers.setChecked(self._remembered("pageNumbers"))
        self.body.setVisible(False)
        self.toggle_button.setText("Change")
        self._update_summary()
