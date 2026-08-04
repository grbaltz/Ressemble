from PySide6.QtCore import QObject, Signal
from src.assembler import assemble_report
import threading

class AssembleWorker(QObject):
    finished = Signal()
    log = Signal(str)
    progress = Signal(str)
    request_advisors = Signal(str)

    def __init__(self):
        super().__init__()
        self._advisors = None
        self._wait = threading.Event()
    
    def run(self):
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Assembling Report")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            assemble_report(
                # client_name=self.client_name,
                log=self.log.emit,
                # progress=self.progress.emit,
                request_advisors=self.get_advisors
            )
        except AdvisorsCancelled:
            self.log.emit("Advisor selection cancelled by user.")
        finally:
            self.finished.emit()
            
    def get_advisors(self, dir):
        print("Attempting to get advisors")
        self._advisors = None
        self._wait.clear()

        self.request_advisors.emit(dir)

        self._wait.wait()
        
        if self._advisors is None:
            raise AdvisorsCancelled()
        
        print("Return _advisors")

        return self._advisors

    def receive_advisors(self, advisors):
        self._advisors = advisors
        self._wait.set()
    
class AdvisorsCancelled(Exception):
    pass