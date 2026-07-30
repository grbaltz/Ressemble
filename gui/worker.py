from PySide6.QtCore import QObject, Signal
from src.matcher import prepare_report
from src.assembler import assemble_report
import threading

            
class ScanWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal()
    requestLabel = Signal(str) # str for filename, __ for pixmap later
    # labelProvided = Signal(str)
    
    def __init__(self, pdf):
        super().__init__()
        self.pdf = pdf
        self._label = None
        self._placeholder = "n"
        self._wait = threading.Event()

    def run(self):
        try:
            prepare_report(
                pdf=self.pdf,
                log=self.log.emit,
                progress=self.progress.emit,
                requestLabel=self.request_label
            )
        except ScanCancelled:
            self.log.emit("Scan cancelled by user.")
        finally:
            self.finished.emit()
            
    def request_label(self, filename):
        self._label = None
        self._placeholder = False
        self._wait.clear()

        self.requestLabel.emit(filename)

        self._wait.wait()
        
        if self._label is None:
            raise ScanCancelled()

        return self._label, self._placeholder

    def receive_label(self, label, placeholder):        
        self._label = label
        self._placeholder = placeholder
        self._wait.set()
            
class AssembleWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    finished = Signal()

    def __init__(self, pdf, output, client_name):
        super().__init__()
        
        self.pdf = pdf
        self.output = output
        self.client_name = client_name

    def run(self):
        try:
            assemble_report(
                pdf=self.pdf,
                output=self.output,
                client_name=self.client_name,
                log=self.log.emit,
                progress=self.progress.emit,
            )
            
        finally:
            self.finished.emit()
            
class ScanCancelled(Exception):
    pass