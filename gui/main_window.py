from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import QSettings
import json
from gui.screens.select_template_screen import SelectTemplateScreen
from gui.screens.scan_screen import ScanScreen
from gui.screens.sources_advisors_screen import SourcesAdvisorsScreen
from gui.screens.details_screen import DetailsScreen
from gui.screens.compile_screen import CompileScreen
from src.paths import TEMPLATE_CONFIG_PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Rebalance", "Ressemble")

        self.setWindowTitle("Ressemble")
        # Fixed, not just an initial resize() -- a child widget with
        # unwrapped dynamic content (long filenames, a joined names list,
        # etc.) can otherwise force the whole window wider/taller than
        # intended. Content that doesn't fit should wrap or clip, not grow
        # the window.
        self.setFixedSize(700, 760)

        # Shared state, populated as the wizard progresses.
        self.scan_results = None
        self.pdf_path = ""
        self.matched_pages = None
        self.client_name = ""
        self.target_date = None
        self.enrolled = False
        self.include_page_numbers = True

        self.stack = QStackedWidget()

        self.select_template_screen = SelectTemplateScreen(self, self.settings)
        self.sources_advisors_screen = SourcesAdvisorsScreen(self, self.settings)
        self.details_screen = DetailsScreen(self, self.settings)
        self.compile_screen = CompileScreen(self, self.settings)
        # Scan screen is created last -- if a template's already on file it
        # kicks off scanning immediately in its own constructor, and by then
        # the screens it can hand off to already exist.
        self.scan_screen = ScanScreen(self, self.settings)

        self.select_template_screen.template_selected.connect(self._on_template_selected)

        self.stack.addWidget(self.select_template_screen)
        self.stack.addWidget(self.scan_screen)
        self.stack.addWidget(self.sources_advisors_screen)
        self.stack.addWidget(self.details_screen)
        self.stack.addWidget(self.compile_screen)

        self.setCentralWidget(self.stack)

        # Only a completely fresh install (no template saved yet) sees
        # SelectTemplateScreen -- every later launch goes straight to
        # ScanScreen, which loads the saved template itself.
        if self._has_template():
            self.stack.setCurrentWidget(self.scan_screen)

    def _has_template(self):
        try:
            with open(TEMPLATE_CONFIG_PATH) as template_config:
                config = json.load(template_config)
        except (FileNotFoundError, json.JSONDecodeError):
            return False
        return bool(config.get("filename"))

    def _on_template_selected(self, filename):
        self.stack.setCurrentWidget(self.scan_screen)
        self.scan_screen.start_with(filename)

    def restart(self):
        self.scan_results = None
        self.client_name = ""
        self.target_date = None
        self.enrolled = False
        self.include_page_numbers = True

        # matched_pages/pdf_path deliberately survive a restart -- the
        # template was already scanned and hasn't changed, so there's
        # nothing for ScanScreen to redo. It only re-scans when the user
        # actually picks a different template file (see ScanScreen._use_pdf).
        self.sources_advisors_screen.reset()
        self.details_screen.reset()
        self.compile_screen.reset()

        self.stack.setCurrentWidget(self.scan_screen)
