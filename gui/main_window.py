from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import QSettings
from gui.screens.scan_screen import ScanScreen
from gui.screens.sources_advisors_screen import SourcesAdvisorsScreen
from gui.screens.details_screen import DetailsScreen
from gui.screens.compile_screen import CompileScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Rebalance", "Ressemble")

        self.setWindowTitle("Ressemble")
        self.resize(700, 760)

        # Shared state, populated as the wizard progresses.
        self.scan_results = None
        self.client_name = ""
        self.target_date = None
        self.enrolled = False
        self.include_page_numbers = True

        self.stack = QStackedWidget()

        self.sources_advisors_screen = SourcesAdvisorsScreen(self, self.settings)
        self.details_screen = DetailsScreen(self, self.settings)
        self.compile_screen = CompileScreen(self, self.settings)
        # Scan screen is created last -- it kicks off scanning immediately,
        # and by then the screens it can hand off to already exist.
        self.scan_screen = ScanScreen(self, self.settings)

        self.stack.addWidget(self.scan_screen)
        self.stack.addWidget(self.sources_advisors_screen)
        self.stack.addWidget(self.details_screen)
        self.stack.addWidget(self.compile_screen)

        self.setCentralWidget(self.stack)

    def restart(self):
        self.scan_results = None
        self.client_name = ""
        self.target_date = None
        self.enrolled = False
        self.include_page_numbers = True

        self.sources_advisors_screen.reset()
        self.details_screen.reset()
        self.compile_screen.reset()

        self.stack.setCurrentWidget(self.scan_screen)
        self.scan_screen.scan_pdf(refresh=False)
