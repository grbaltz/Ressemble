from PySide6.QtCore import QObject, Signal
from src.matcher import prepare_report, get_page_pixmap
from src.assembler import assemble_report
import threading
            
class ScanWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal()
    request_label = Signal(str, bytes) # str for filename, bytes for pixmap later
    request_replacements = Signal(str, str, bytes)
    
    def __init__(self, pdf):
        super().__init__()
        self.pdf = pdf
        self._label = None
        self._placeholder = False
        self._pix_bytes = None
        self._replacement_filenames = None
        self._wait = threading.Event()

    def run(self):
        try:
            prepare_report(
                pdf=self.pdf,
                log=self.log.emit,
                progress=self.progress.emit,
                request_label=self.get_label,
                request_replacements=self.get_replacements
            )
        except ScanCancelled:
            self.log.emit("Scan cancelled by user.")
        finally:
            self.finished.emit()
            
    # Labeling logic
    def get_label(self, filename, pix_bytes):
        self._label = None
        self._placeholder = False
        self._wait.clear()

        self.request_label.emit(filename, pix_bytes)

        self._wait.wait()
        
        if self._label is None:
            raise ScanCancelled()

        return self._label, self._placeholder

    def receive_label(self, label, placeholder):        
        self._label = label
        self._placeholder = placeholder
        self._wait.set()
        
    # Replacement logic
    def get_replacements(self, filename, label, pix_bytes):
        self._replacement_filenames
        self._wait.clear()
        
        self.request_replacements.emit(filename, label, pix_bytes)
        
        self._wait.wait() 
        
        if self._replacement_filenames is None:
            raise ReplacementCancelled()

        return self._replacement_filenames
        
    def receive_replacements(self, filenames):
        self._replacement_filenames = filenames
        
        self._wait.set()
            
class ScanCancelled(Exception):
    pass

class ReplacementCancelled(Exception):
    pass