from PySide6.QtWidgets import QComboBox


class NoWheelComboBox(QComboBox):
    """A combo box that ignores the mouse wheel. By default scrolling while
    the pointer happens to be over one cycles its selection, which silently
    changes a team or role when the user only meant to scroll the page.
    Ignoring the event hands it on to the scroll area underneath."""

    def wheelEvent(self, event):
        event.ignore()
