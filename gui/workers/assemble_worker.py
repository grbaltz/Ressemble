from PySide6.QtCore import QObject, Signal
from src.assembler import assemble_report_in_subprocess
import multiprocessing
import queue

POLL_INTERVAL_S = 0.2

class AssembleWorker(QObject):
    finished = Signal(object) # report_path, or None on failure/cancel
    log = Signal(str)
    progress = Signal(int, int) # current, total

    def __init__(self, matched_pages, sources, advisors_file, client_name, enrolled, target_date=None, include_page_numbers=True, include_plan_360=True):
        super().__init__()
        self._kwargs = dict(
            advisors_filename=advisors_file,
            client_name=client_name,
            enrolled=enrolled,
            target_date=target_date,
            include_page_numbers=include_page_numbers,
            include_plan_360=include_plan_360,
        )
        self._process = None
        self._cancelled = False

    def run(self):
        # The actual assembly runs in a child process (see
        # assemble_report_in_subprocess for why); this thread just relays
        # its messages to the GUI as signals.
        report_path = None
        done = False
        ctx = multiprocessing.get_context("spawn")
        messages = ctx.Queue()
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Assembling Report")
            self.log.emit("------------------------------------------------------------------------------------------------------")

            self._process = ctx.Process(
                target=assemble_report_in_subprocess,
                args=(messages, self._kwargs),
                daemon=True,
            )
            if self._cancelled:
                return
            self._process.start()

            while not done:
                try:
                    message = messages.get(timeout=POLL_INTERVAL_S)
                except queue.Empty:
                    if self._process.is_alive():
                        continue
                    # Exited between polls -- pick up anything it managed
                    # to send on the way out before giving up on it.
                    while not done:
                        try:
                            message = messages.get_nowait()
                        except (queue.Empty, EOFError, OSError):
                            break
                        done, report_path = self._handle(message, report_path)
                    break
                except (EOFError, OSError):
                    break
                done, report_path = self._handle(message, report_path)

            if self._cancelled:
                report_path = None
                self.log.emit("Compile cancelled.")
            elif not done:
                self.log.emit(f"Compile process exited unexpectedly (exit code {self._process.exitcode}).")
        except Exception as e:
            report_path = None
            self.log.emit(f"Error: {e}")
        finally:
            if self._process is not None and self._process.is_alive():
                self._process.terminate()
            if self._process is not None and self._process.pid is not None:
                self._process.join(timeout=2)
            messages.close()
            self.finished.emit(report_path)

    def _handle(self, message, report_path):
        kind = message[0]
        if kind == "log":
            self.log.emit(message[1])
        elif kind == "progress":
            self.progress.emit(message[1], message[2])
        elif kind == "done":
            return True, message[1]
        elif kind == "error":
            self.log.emit(message[1])
            return True, None
        return False, report_path

    def cancel(self):
        # Called from the GUI thread. Killing the process is what makes
        # cancelling possible at all -- a thread stuck inside a PyMuPDF
        # call can't be interrupted.
        self._cancelled = True
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
