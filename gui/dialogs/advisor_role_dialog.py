from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from src.advisors import ROLE_ADVISOR, ROLE_SERVICE, save_advisor_roles

class AdvisorRoleDialog(QDialog):
    """Asks whether one team member is an advisor or service. The result
    decides which Sources & Advisors dropdowns they show up in."""

    def __init__(self, name, position, total, current_role=None, parent=None):
        super().__init__(parent)

        self.role = None

        self.setWindowTitle("Classify Team Member")

        title = QLabel(name)
        title.setProperty("class", "title")

        message = QLabel(f"Team member {position} of {total} -- is this person an advisor or service?")
        message.setProperty("class", "subtitle")
        message.setWordWrap(True)

        # A plain row rather than QDialogButtonBox, which reorders buttons
        # by platform convention -- this order should always be fixed.
        advisor_button = QPushButton("Advisor")
        service_button = QPushButton("Service")
        skip_button = QPushButton("Skip the Rest")

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        buttons.addWidget(advisor_button)
        buttons.addWidget(service_button)
        buttons.addWidget(skip_button)

        advisor_button.clicked.connect(lambda: self._choose(ROLE_ADVISOR))
        service_button.clicked.connect(lambda: self._choose(ROLE_SERVICE))
        skip_button.clicked.connect(self.reject)

        # Re-classifying someone: Enter keeps their existing role.
        default = service_button if current_role == ROLE_SERVICE else advisor_button
        default.setDefault(True)
        default.setFocus()

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def _choose(self, role):
        self.role = role
        self.accept()


def classify_advisors(names, parent=None, current_roles=None):
    """Prompts for each name in turn, saving each answer as soon as it's
    given (so a "Skip the Rest" partway through keeps everything answered
    up to that point). Returns how many were classified."""
    current_roles = current_roles or {}
    classified = 0
    for position, name in enumerate(names, start=1):
        dlg = AdvisorRoleDialog(name, position, len(names), current_roles.get(name), parent)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.role is None:
            break
        save_advisor_roles({name: dlg.role})
        classified += 1
    return classified
