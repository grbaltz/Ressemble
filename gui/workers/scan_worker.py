from PySide6.QtCore import QObject, Signal
from src.scanner import prepare_report, get_page_pixmap, select_advisor_file
import threading

class ScanWorker(QObject):
    log = Signal(str)
    progress = Signal(int, int) # current, total
    finished = Signal(object)
    request_label = Signal(str, bytes) # str for filename, bytes for pixmap later
    request_sources_and_advisors = Signal()

    def __init__(self, pdf, refresh):
        super().__init__()
        self.pdf = pdf
        self._label = None
        self._pix_bytes = None
        self._matched_pages = None
        self._sources = None
        self._advisors = None
        self._sources_and_advisors_resolved = False
        self._advisors_file = None
        self.refresh = refresh
        self._wait = threading.Event()

    def run(self):
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Beginning Template Scan")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            matched_pages, sources = prepare_report(
                pdf=self.pdf,
                refresh=self.refresh,
                log=self.log.emit,
                progress=self.progress.emit,
                request_label=self.get_label,
                request_sources=self.get_sources
            )
            self._matched_pages = matched_pages
            self._sources = sources
            advisors_file = select_advisor_file(
                log=self.log.emit,
                request_advisors=self.get_advisors
            )
            self._advisors_file = advisors_file
        except ScanCancelled:
            self.log.emit("Scan cancelled by user.")
        except SourcesCancelled:
            self.log.emit("Sources cancelled by user.")
        except AdvisorsCancelled:
            self.log.emit("Advisor selection cancelled by user.")
        finally:
            self.finished.emit({
                "matched_pages": self._matched_pages,
                "sources": self._sources,
                "advisors_file": self._advisors_file
            })

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

    # Sources + advisors are always both required, every run, with no user
    # interaction in between (save_template/get_emx_order/get_bd_order) --
    # so they're gathered together in one round trip and cached, even though
    # scanner.py asks for them via two separate calls.
    def get_sources(self):
        if not self._sources_and_advisors_resolved:
            self._resolve_sources_and_advisors()

        if self._sources is None:
            raise SourcesCancelled()

        return self._sources

    def get_advisors(self):
        if not self._sources_and_advisors_resolved:
            self._resolve_sources_and_advisors()

        if self._advisors is None:
            raise AdvisorsCancelled()

        return self._advisors

    def _resolve_sources_and_advisors(self):
        self._wait.clear()

        self.request_sources_and_advisors.emit()

        self._wait.wait()

        self._sources_and_advisors_resolved = True

    def receive_sources_and_advisors(self, sources, advisors):
        self._sources = sources
        self._advisors = advisors
        self._wait.set()

class ScanCancelled(Exception):
    pass

class SourcesCancelled(Exception):
    pass

class AdvisorsCancelled(Exception):
    pass
