from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PySide6.QtCore import QSettings, QTimer, QEvent
from gui.screens.builder_screen import BuilderScreen
from gui.screens.library_screen import LibraryScreen
from gui.widgets.app_header import AppHeader
from gui.widgets.fit import CurrentStack

SCREEN_BUILDER = 0
SCREEN_LIBRARY = 1

WINDOW_WIDTH = 960
# Never shorter than this, so a nearly empty screen doesn't look cramped.
MIN_WINDOW_HEIGHT = 520
# Room left for the title bar's own height and the taskbar/dock margins.
SCREEN_MARGIN = 24


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Rebalance", "Ressemble")

        self.setWindowTitle("Ressemble")
        # The width is fixed and the height follows the content (see
        # _fit_height) -- fixed rather than free-form because a child widget
        # with unwrapped dynamic content (long filenames, a joined names
        # list, etc.) could otherwise force the window wider than intended.
        # Content that doesn't fit should wrap, elide or scroll, not grow
        # the window sideways.
        self.setFixedWidth(WINDOW_WIDTH)
        self._fit_pending = False

        # Shared with the Builder, which needs them to start a build: set by
        # the Library whenever the template finishes scanning.
        self.pdf_path = ""
        self.matched_pages = None

        self.header = AppHeader()
        self.builder_screen = BuilderScreen(self, self.settings)
        # Created last -- if a template's already on file it starts
        # scanning immediately in its own constructor, and by then the
        # screen it reports to already exists.
        self.library_screen = LibraryScreen(self, self.settings)

        self.stack = CurrentStack()
        self.stack.addWidget(self.builder_screen)
        self.stack.addWidget(self.library_screen)

        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.stack, 1)
        central.setLayout(layout)
        self.setCentralWidget(central)
        central.installEventFilter(self)

        # Until first-time setup is done (template, advisors and tear sheets
        # all provided, then Continue), the Library is the only place to be
        # and the builder stays out of reach.
        self._first_run_pending = self.library_screen.setup_pending()

        self.header.library_clicked.connect(self._toggle_library)
        self.library_screen.status_changed.connect(self._on_library_status)
        self.library_screen.template_ready_changed.connect(self._sync_builder)
        self.library_screen.setup_finished.connect(self._on_setup_finished)
        self.builder_screen.library_changed.connect(self.library_screen.refresh_status)

        self._sync_builder()
        self.library_screen.refresh_status()

        if self._first_run_pending:
            self._show_library()
            self.header.library_button.setVisible(False)
        else:
            self._show_builder()

    # --- navigation ---

    def _show_builder(self):
        self.stack.setCurrentIndex(SCREEN_BUILDER)
        self._schedule_fit()
        self.header.show_library_button()
        self.header.set_dot_visible(True)

    def _show_library(self):
        self.stack.setCurrentIndex(SCREEN_LIBRARY)
        self._schedule_fit()
        self.header.show_back_button()
        self.header.set_dot_visible(False)

    def _toggle_library(self):
        if self.stack.currentIndex() == SCREEN_LIBRARY:
            self._show_builder()
        else:
            self._show_library()

    # --- library -> header / builder ---

    def _on_library_status(self, state, tooltip):
        self.header.set_status(state, tooltip)
        self._sync_builder()

    def _on_setup_finished(self):
        # Only the user's own Continue gets them out of first-time setup --
        # a finished scan alone isn't enough, the other files are needed too.
        self._first_run_pending = False
        self.header.library_button.setVisible(True)
        self._show_builder()

    def _sync_builder(self, *_):
        self.builder_screen.set_template_state(
            self.library_screen.scanning(),
            self.library_screen.template_ready(),
        )

    # --- window height ---

    def eventFilter(self, watched, event):
        # Anything that changes how tall the content wants to be (a section
        # appearing, options expanding, switching screens) invalidates the
        # layout, which the central widget receives as a layout request.
        if watched is self.centralWidget() and event.type() == QEvent.Type.LayoutRequest:
            self._schedule_fit()
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_fit()

    def _schedule_fit(self):
        if not self._fit_pending:
            self._fit_pending = True
            QTimer.singleShot(0, self._fit_height)

    def _fit_height(self):
        """Sizes the window to its content, up to what the screen allows --
        a scrollbar only appears once the content outgrows the screen."""
        self._fit_pending = False

        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry()
        # The title bar and borders around the window's content area.
        chrome = max(self.frameGeometry().height() - self.height(), 0)

        # Asked of the parts directly: the central layout caches its own
        # size hint and can still report the previous screen's height.
        wanted = self.header.height() + self.stack.sizeHint().height()
        height = max(MIN_WINDOW_HEIGHT, min(wanted, available.height() - chrome - SCREEN_MARGIN))

        if height != self.height():
            self.setFixedHeight(height)
            # Growing downward can push the bottom edge off the screen.
            overflow = self.frameGeometry().bottom() - available.bottom()
            if overflow > 0:
                self.move(self.x(), max(available.top(), self.y() - overflow))

    # --- lifecycle ---

    def restart(self):
        # pdf_path/matched_pages deliberately survive a restart -- the
        # template was already scanned and hasn't changed, so there's
        # nothing to redo. It only re-scans when the user actually picks a
        # different template file (see LibraryScreen._use_pdf).
        self.builder_screen.reset()
        self._show_builder()

    def closeEvent(self, event):
        self.builder_screen.runner.stop()
        super().closeEvent(event)
