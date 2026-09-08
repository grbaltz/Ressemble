from PySide6.QtCore import QObject, Signal
from src.scanner import finish_sources

class FinishSourcesWorker(QObject):
    """Runs everything that depends on the EMX/BD files and the advisor
    selection -- resolving/ordering the sources and persisting the advisor
    combination -- after the Sources screen submits. Independent of
    ScanWorker: the template itself was already fingerprinted before this
    ever runs."""

    log = Signal(str)
    finished = Signal(object) # sources dict, or None on failure

    def __init__(self, pdf, matched_pages, emx_pdf, blackdiamond_pdf, selected_advisors):
        super().__init__()
        self.pdf = pdf
        self.matched_pages = matched_pages
        self.emx_pdf = emx_pdf
        self.blackdiamond_pdf = blackdiamond_pdf
        self.selected_advisors = selected_advisors

    def run(self):
        sources = None
        try:
            self.log.emit("------------------------------------------------------------------------------------------------------")
            self.log.emit("Processing Sources")
            self.log.emit("------------------------------------------------------------------------------------------------------")
            sources = finish_sources(
                pdf=self.pdf,
                matched_pages=self.matched_pages,
                emx_pdf=self.emx_pdf,
                blackdiamond_pdf=self.blackdiamond_pdf,
                selected_advisors=self.selected_advisors,
                log=self.log.emit,
            )
        except Exception as exc:
            self.log.emit(f"Error processing sources: {exc}")
        finally:
            self.finished.emit(sources)
