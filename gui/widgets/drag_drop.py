from pathlib import Path


def dropped_file_path(mime_data, extensions):
    """Returns the local path of the first dropped file whose extension is
    in `extensions`, or None if the drag doesn't carry a matching one.
    Used both to decide whether to accept a drag as it enters a widget and
    to pull the actual path out once it's dropped."""
    if not mime_data.hasUrls():
        return None

    allowed = {ext.lower() for ext in extensions}
    for url in mime_data.urls():
        if url.isLocalFile():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in allowed:
                return path
    return None


class FileDropTargetMixin:
    """Mix into a QWidget to let it accept a single file of a given type
    dragged in from the OS (Finder, Explorer, a file manager) anywhere on
    the widget, as an alternative to browsing for it.

    Call _enable_file_drop(extensions) once (typically in __init__) and
    override _handle_dropped_file(path). Left out of WizardScreen itself
    since not every screen wants to be a drop target, and the ones that do
    disagree on what a drop should mean.
    """

    def _enable_file_drop(self, extensions):
        self._drop_extensions = extensions
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if dropped_file_path(event.mimeData(), self._drop_extensions):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if dropped_file_path(event.mimeData(), self._drop_extensions):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        path = dropped_file_path(event.mimeData(), self._drop_extensions)
        if path:
            event.acceptProposedAction()
            self._handle_dropped_file(path)
        else:
            event.ignore()
