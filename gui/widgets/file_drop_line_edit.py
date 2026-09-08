from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Signal
from gui.widgets.drag_drop import dropped_file_path


class FileDropLineEdit(QLineEdit):
    """A read-only path display that doubles as a drop target -- dragging a
    matching file from Finder/Explorer onto it fills it in exactly like
    picking one via the adjacent Browse button would."""

    file_dropped = Signal(str)

    def __init__(self, extensions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extensions = extensions
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if dropped_file_path(event.mimeData(), self._extensions):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._set_drag_active(False)
        path = dropped_file_path(event.mimeData(), self._extensions)
        if path:
            event.acceptProposedAction()
            self.file_dropped.emit(path)
        else:
            event.ignore()

    def _set_drag_active(self, active):
        # Repolish is needed for a dynamic property change to actually
        # affect a stylesheet selector after the widget's already shown.
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)
