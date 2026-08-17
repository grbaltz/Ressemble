from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy, QApplication
from PySide6.QtCore import Qt, QEvent


class WizardScreen(QWidget):
    """Base class for a full-page wizard step.

    Lays out a title, optional subtitle, a content area subclasses populate
    via `content_layout`, and a bottom button row with an optional back
    button and a primary (accent) button. Enter/Return anywhere on the
    screen triggers the primary button, mirroring QDialog's default-button
    behavior (which plain QWidgets don't get for free).
    """

    def __init__(self, title, subtitle=None):
        super().__init__()

        outer = QVBoxLayout()
        outer.setContentsMargins(48, 40, 48, 32)
        outer.setSpacing(20)

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "title")
        outer.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle or "")
        self.subtitle_label.setProperty("class", "subtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        outer.addWidget(self.subtitle_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(16)
        outer.addLayout(self.content_layout)

        outer.addStretch(1)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        self.back_button = QPushButton("Back")
        self.back_button.setProperty("class", "link")
        self.back_button.setVisible(False)
        self.back_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button_row.addWidget(self.back_button)

        button_row.addStretch(1)

        self.primary_button = QPushButton("Continue")
        self.primary_button.setProperty("class", "primary")
        self.primary_button.setDefault(True)
        self.primary_button.setAutoDefault(True)
        self.primary_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.primary_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button_row.addWidget(self.primary_button)

        outer.addLayout(button_row)

        self.setLayout(outer)

        self._primary_connected = False
        self._back_connected = False

    def set_title(self, text):
        self.title_label.setText(text)

    def set_subtitle(self, text):
        self.subtitle_label.setText(text or "")
        self.subtitle_label.setVisible(bool(text))

    def set_primary(self, text=None, enabled=None, callback=None, visible=True):
        if text is not None:
            self.primary_button.setText(text)
        if enabled is not None:
            self.primary_button.setEnabled(enabled)
        if callback is not None:
            if self._primary_connected:
                self.primary_button.clicked.disconnect()
            self.primary_button.clicked.connect(callback)
            self._primary_connected = True
        self.primary_button.setVisible(visible)

    def set_back(self, callback=None, visible=True):
        if callback is not None:
            if self._back_connected:
                self.back_button.clicked.disconnect()
            self.back_button.clicked.connect(callback)
            self._back_connected = True
        self.back_button.setVisible(visible)

    # Enter needs to advance the wizard no matter which child widget has
    # focus (QLineEdit, QDateEdit, QListWidget, QCheckBox...). Widgets like
    # QLineEdit *accept* the Return key themselves for their own signals, so
    # a plain keyPressEvent override here would never see it -- installing
    # an application-level filter while this screen is the visible one lets
    # us intercept before it's delivered to the child at all.
    def showEvent(self, event):
        super().showEvent(event)
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event):
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        super().hideEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            focused = QApplication.focusWidget()
            if focused is not None and self.isAncestorOf(focused):
                if self.primary_button.isVisible() and self.primary_button.isEnabled():
                    self.primary_button.click()
                    return True
        return super().eventFilter(watched, event)
