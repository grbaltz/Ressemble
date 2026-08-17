from PySide6.QtCore import QObject, Signal
from src.assembler import assemble_report
import threading

class AssembleWorker(QObject):
    finished = Signal(object) # report_path
    log = Signal(str)
    progress = Signal(int, int) # current, total

    def __init__(self, matched_pages, sources, advisors_file, client_name, enrolled, target_date=None):
        super().__init__()
        self._advisors_file = advisors_file
        self._client_name = client_name
        self._enrolled = enrolled
        self._target_date = target_date
        self._wait = threading.Event()

    def run(self):
        report_path = None
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Assembling Report")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            report_path = assemble_report(
                log=self.log.emit,
                progress=self.progress.emit,
                advisors_filename=self._advisors_file,
                client_name=self._client_name,
                enrolled=self._enrolled,
                target_date=self._target_date
            )
        finally:
            self.finished.emit(report_path)
