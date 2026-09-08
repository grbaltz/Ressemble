from PySide6.QtWidgets import QPushButton, QFileDialog
from PySide6.QtCore import Qt, Signal
from gui.widgets.wizard_screen import WizardScreen
from gui.widgets.drag_drop import FileDropTargetMixin
from pathlib import Path

TEMPLATE_EXTENSIONS = {".pdf"}

class SelectTemplateScreen(FileDropTargetMixin, WizardScreen):
    """Shown once, on a completely fresh install with no template on file.

    There's nothing to go back to and nothing to continue past -- browsing
    for a template is the only thing this screen can do -- so both of
    WizardScreen's bottom buttons are hidden in favor of a single explicit
    action button. Also accepts a PDF dragged in from Finder/Explorer
    anywhere on the screen, since there's no other content competing for
    the drop.
    """

    template_selected = Signal(str)

    def __init__(self, main_window, settings):
        super().__init__(
            "Welcome to Ressemble",
            "Before you can prepare a report, select the default report "
            "template -- the master PDF containing every possible report "
            "page and its placeholders. Ressemble scans it once and reuses "
            "it for every report after that. Drag it in, or browse for it "
            "below."
        )
        self.main_window = main_window
        self.settings = settings

        self.set_primary(visible=False)
        self.set_back(visible=False)
        self._enable_file_drop(TEMPLATE_EXTENSIONS)

        self.browse_button = QPushButton("Browse for Template…")
        self.browse_button.setProperty("class", "primary")
        self.browse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.browse_button.clicked.connect(self._choose_template)
        self.content_layout.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def _choose_template(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Report Template",
            self.settings.value("lastTemplateDir"),
            "PDF Files (*.pdf)"
        )

        if filename:
            self._use_template(filename)

    def _handle_dropped_file(self, path):
        self._use_template(path)

    def _use_template(self, filename):
        self.settings.setValue("lastTemplateDir", str(Path(filename).parent))
        self.template_selected.emit(filename)
