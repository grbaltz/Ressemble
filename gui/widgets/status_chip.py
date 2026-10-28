from PySide6.QtWidgets import QLabel, QSizePolicy
from gui.theme import repolish


class StatusChip(QLabel):
    """A small rounded status pill: state is "ok", "warn" or "busy"."""

    def __init__(self, text="", state="ok", parent=None):
        super().__init__(text, parent)
        self.setProperty("class", "chip")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_state(state)

    def set_status(self, text, state):
        self.setText(text)
        self.set_state(state)

    def set_state(self, state):
        self.setProperty("state", state)
        repolish(self)
