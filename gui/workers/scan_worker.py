from PySide6.QtCore import QObject, Signal
from src.scanner import prepare_report, get_page_pixmap, select_advisor_file
import threading
            
class ScanWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal(object)
    request_label = Signal(str, bytes) # str for filename, bytes for pixmap later
    request_sources = Signal()
    request_advisors = Signal()
    
    def __init__(self, pdf, refresh):
        super().__init__()
        self.pdf = pdf
        self._label = None
        self._slot = False
        self._pix_bytes = None
        self._matched_pages = None
        self._sources = None
        self._advisors_file = None
        self.refresh = refresh
        self._wait = threading.Event()

    def run(self):
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Beginning Template Scan")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            print("Moving on immediately TEST")
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
            print("Advisor selection cancelled by user.")
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
        self._slot = False
        self._wait.clear()

        self.request_label.emit(filename, pix_bytes)

        self._wait.wait()
        
        if self._label is None:
            raise ScanCancelled()

        return self._label, self._slot

    def receive_label(self, label, slot):        
        self._label = label
        self._slot = slot
        self._wait.set()
        
    def get_sources(self):
        self._sources = None
        
        self._wait.clear()
        
        self.request_sources.emit()
        
        self._wait.wait()

        return self._sources
        
    def receive_sources(self, filenames):
        print(f"Received source filenames {filenames}")
        self._sources = filenames
        
        self._wait.set()
    
    def get_advisors(self):
        print("Attempting to get advisors")
        self._advisors = None
        self._wait.clear()

        self.request_advisors.emit()

        self._wait.wait()
        
        if self._advisors is None:
            raise AdvisorsCancelled()
        
        print("Return _advisors")

        return self._advisors

    def receive_advisors(self, advisors):
        print(f"Accepting {advisors}")
        self._advisors = advisors
        self._wait.set()
            
class ScanCancelled(Exception):
    pass

class SourcesCancelled(Exception):
    pass

class AdvisorsCancelled(Exception):
    pass