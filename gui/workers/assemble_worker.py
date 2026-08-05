from PySide6.QtCore import QObject, Signal
from src.assembler import assemble_report
import threading

class AssembleWorker(QObject):
    finished = Signal()
    log = Signal(str)
    progress = Signal(str)

    def __init__(self, matched_pages, sources, advisors_file, client_name, enrolled):
        super().__init__()
        self._advisors_file = advisors_file
        self._client_name = client_name
        self._enrolled = enrolled
        self._wait = threading.Event()
    
    def run(self):
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Assembling Report")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            assemble_report(
                log=self.log.emit,
                progress=self.progress.emit,
                advisors_filename=self._advisors_file,
                client_name=self._client_name,
                enrolled=self._enrolled
            )
        finally:
            self.finished.emit()
