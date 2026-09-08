from PySide6.QtCore import QObject, Signal
from src.scanner import scan_template
import threading

class ScanWorker(QObject):
    log = Signal(str)
    progress = Signal(int, int) # current, total
    finished = Signal(object) # matched_pages, or None if cancelled
    request_label = Signal(str, bytes) # str for filename, bytes for pixmap later

    def __init__(self, pdf, refresh):
        super().__init__()
        self.pdf = pdf
        self._label = None
        self._matched_pages = None
        self.refresh = refresh
        self._wait = threading.Event()

    def run(self):
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Beginning Template Scan")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self._matched_pages = scan_template(
                pdf=self.pdf,
                refresh=self.refresh,
                log=self.log.emit,
                progress=self.progress.emit,
                request_label=self.get_label,
            )
        except ScanCancelled:
            self.log.emit("Scan cancelled by user.")
        finally:
            self.finished.emit(self._matched_pages)

    # Labeling logic
    def get_label(self, filename, pix_bytes):
        self._label = None
        self._wait.clear()

        self.request_label.emit(filename, pix_bytes)

        self._wait.wait()

        if self._label is None:
            raise ScanCancelled()

        return self._label

    def receive_label(self, label):
        self._label = label
        self._wait.set()

class ScanCancelled(Exception):
    pass
