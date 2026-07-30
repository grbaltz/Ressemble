from PySide6.QtCore import QObject, Signal
from src.assembler import assemble_report
import threading

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