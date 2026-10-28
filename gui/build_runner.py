from dataclasses import dataclass
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from gui.workers.finish_sources_worker import FinishSourcesWorker
from gui.workers.assemble_worker import AssembleWorker

# How long a build may go without any progress or log output before the
# user is offered a retry. Building keeps going in the meantime -- it may
# just be a slow merge -- so this only prompts, it never kills the run.
STALL_TIMEOUT_MS = 20_000

STAGE_SOURCES = "sources"
STAGE_ASSEMBLE = "assemble"


@dataclass
class BuildParams:
    pdf: str
    matched_pages: object
    emx_pdf: str
    blackdiamond_pdf: str
    advisors: list
    client_name: str
    enrolled: bool
    target_date: object
    include_page_numbers: bool
    include_plan_360: bool


class BuildRunner(QObject):
    """Runs one report build as two stages back to back: processing the EMX
    and Black Diamond sources (a thread -- see FinishSourcesWorker), then
    assembling the report (its own process -- see AssembleWorker). Owns the
    stall timer and the bookkeeping that lets a cancelled or retried run
    wind down in the background without its late signals reaching the UI.
    """

    status = Signal(str)
    progress = Signal(int, int)
    log = Signal(str)
    stalled = Signal()
    resumed = Signal()
    # (report_path or None, "done" | "cancelled" | "failed")
    finished = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._params = None
        self._worker = None
        self._stage = None
        self._stalled = False
        self._start_pending = False
        # (thread, worker) pairs kept referenced until their thread stops,
        # so a cancelled run can wind down after a retry has replaced it.
        self._jobs = []

        self._stall_timer = QTimer(self)
        self._stall_timer.setSingleShot(True)
        self._stall_timer.setInterval(STALL_TIMEOUT_MS)
        self._stall_timer.timeout.connect(self._on_stalled)

    def is_running(self):
        return self._worker is not None

    def start(self, params):
        """Also serves as "Try Again" -- any run still going is stopped
        first, and its late signals are ignored (see _is_current)."""
        self.stop()
        self._prune_jobs()
        self._params = params
        self._stalled = False

        # An abandoned run's thread can't be killed, and two runs writing
        # the same split-page folders at once would corrupt each other, so
        # a new run waits for any such thread to wind down first.
        if self._jobs:
            self._start_pending = True
            self.status.emit("Finishing the previous attempt…")
            self._stall_timer.start()
            return

        self._start_sources()

    def retry(self):
        if self._params is not None:
            self.start(self._params)

    def acknowledge_stall(self):
        """The user chose to keep waiting -- ask again after another
        timeout rather than never."""
        self._stalled = False
        self._stall_timer.start()

    def cancel(self):
        if self._worker is None:
            return
        self._stall_timer.stop()
        self.status.emit("Cancelling…")

        if self._stage == STAGE_ASSEMBLE:
            # Killing the process is what makes this possible at all; the
            # worker then reports back through its own finished signal.
            self._worker.cancel()
        else:
            # A source-processing thread can't be stopped, so detach from it
            # and let it finish quietly in the background.
            self._worker = None
            self.finished.emit(None, "cancelled")

    def stop(self):
        """Silently abandons any run in progress -- no finished signal."""
        self._stall_timer.stop()
        self._start_pending = False
        if self._worker is not None and self._stage == STAGE_ASSEMBLE:
            self._worker.cancel()
        self._worker = None

    # --- stage 1: sources ---

    def _start_sources(self):
        self._stage = STAGE_SOURCES
        self.status.emit("Preparing sources…")

        params = self._params
        worker = FinishSourcesWorker(
            pdf=params.pdf,
            matched_pages=params.matched_pages,
            emx_pdf=params.emx_pdf,
            blackdiamond_pdf=params.blackdiamond_pdf,
            selected_advisors=params.advisors,
        )
        worker.finished.connect(self._on_sources_finished)
        self._launch(worker)

    def _on_sources_finished(self, sources):
        if not self._is_current():
            return

        if sources is None:
            self._worker = None
            self._stall_timer.stop()
            self.finished.emit(None, "failed")
            return

        self._start_assemble(sources)

    # --- stage 2: assemble ---

    def _start_assemble(self, sources):
        self._stage = STAGE_ASSEMBLE
        self.status.emit("Starting…")

        params = self._params
        worker = AssembleWorker(
            matched_pages=params.matched_pages,
            sources=sources,
            advisors_file=None,
            client_name=params.client_name,
            enrolled=params.enrolled,
            target_date=params.target_date,
            include_page_numbers=params.include_page_numbers,
            include_plan_360=params.include_plan_360,
        )
        worker.finished.connect(self._on_assemble_finished)
        self._launch(worker)

    def _on_assemble_finished(self, report_path):
        if not self._is_current():
            return

        cancelled = self._worker._cancelled
        self._worker = None
        self._stall_timer.stop()
        self._stalled = False

        if report_path:
            self.finished.emit(report_path, "done")
        elif cancelled:
            self.finished.emit(None, "cancelled")
        else:
            self.finished.emit(None, "failed")

    # --- shared ---

    def _launch(self, worker):
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        worker.log.connect(self._on_log)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)

        self._worker = worker
        self._jobs.append((thread, worker))
        thread.start()
        self._stall_timer.start()

    def _on_thread_finished(self):
        # isRunning() can still read True for the thread whose finished
        # signal this is, so drop it explicitly rather than relying on it.
        done = self.sender()
        self._jobs = [(thread, worker) for thread, worker in self._jobs if thread is not done and thread.isRunning()]
        if self._start_pending and not self._jobs:
            self._start_pending = False
            self._start_sources()

    def _is_current(self):
        return self._worker is not None and self.sender() is self._worker

    def _on_log(self, message):
        if not self._is_current():
            return
        self.log.emit(message)
        self._on_activity()

    def _on_progress(self, current, total):
        if not self._is_current():
            return
        self.progress.emit(current, total)
        if self._stage == STAGE_ASSEMBLE:
            if current >= total:
                # Past the last template page, the merge and save still have
                # to run -- say so rather than sitting on "page N of N".
                self.status.emit("Merging pages and saving the report…")
            else:
                self.status.emit(f"Compiling page {current} of {total}…")
        self._on_activity()

    def _on_activity(self):
        self._stall_timer.start()
        if self._stalled:
            self._stalled = False
            self.resumed.emit()

    def _on_stalled(self):
        if self._worker is None:
            return
        self._stalled = True
        self.stalled.emit()

    def _prune_jobs(self):
        self._jobs = [(thread, worker) for thread, worker in self._jobs if thread.isRunning()]
