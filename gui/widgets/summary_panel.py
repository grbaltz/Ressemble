from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer
from gui.icons import icon, icon_label
from gui.theme import repolish, OK, MUTED_TEXT, ON_ACCENT
from gui.widgets.page_preview import PagePreviewPopup


# Rests on a row this long before its page preview opens, so sweeping the
# pointer down the list doesn't flash a preview for every row it crosses.
PREVIEW_DELAY_MS = 250


class ContentRowWidget(QFrame):
    """One line of the contents list. Reports the pointer entering and
    leaving so the panel can show a page preview for rows that have one."""

    entered = Signal(object)
    left = Signal()

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.row = row
        if row.preview is not None:
            self.setMouseTracking(True)

    def enterEvent(self, event):
        super().enterEvent(event)
        if self.row.preview is not None:
            self.entered.emit(self)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.left.emit()


class SummaryPanel(QFrame):
    """The right-hand "Report contents" panel: a live list of what the
    report will include, with one big action button underneath that is
    Build, then Cancel while building, then Start new report."""

    action_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")

        outer = QVBoxLayout()
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(0)

        title = QLabel("Report contents")
        title.setProperty("class", "card-title")
        outer.addWidget(title)
        outer.addSpacing(8)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        outer.addLayout(self.rows_layout)

        outer.addStretch(1)
        outer.addSpacing(14)

        self.build_button = QPushButton("Build report")
        self.build_button.setProperty("class", "primary")
        self.build_button.setIcon(icon("play", ON_ACCENT, 16))
        self.build_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.build_button.setDefault(True)
        self.build_button.setAutoDefault(True)
        self.build_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.build_button.clicked.connect(self.action_clicked)
        outer.addWidget(self.build_button)
        outer.addSpacing(8)

        self.reason_label = QLabel("")
        self.reason_label.setProperty("class", "status")
        self.reason_label.setWordWrap(True)
        self.reason_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.reason_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        outer.addWidget(self.reason_label)

        self.setLayout(outer)

        self._preview_popup = PagePreviewPopup()
        self._preview_row = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DELAY_MS)
        self._preview_timer.timeout.connect(self._show_preview)

    def set_rows(self, rows):
        self._hide_preview()
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Detached right away, not just deleteLater()'d -- until the
                # event loop gets to it the old row would still be painted
                # on top of the new ones.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        for index, row in enumerate(rows):
            if index:
                divider = QFrame()
                divider.setProperty("class", "divider")
                self.rows_layout.addWidget(divider)
            self.rows_layout.addWidget(self._build_row(row))

    def _build_row(self, row):
        widget = ContentRowWidget(row)
        widget.entered.connect(self._on_row_entered)
        widget.left.connect(self._hide_preview)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)

        mark = icon_label("circle-check" if row.included else "circle-dashed", OK if row.included else MUTED_TEXT, 18)
        layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)

        title = QLabel(row.title)
        title.setProperty("class", "row-title")
        if not row.included:
            title.setStyleSheet(f"color: {MUTED_TEXT};")
        text.addWidget(title)

        detail = QLabel(self._breakable(row.detail))
        detail.setProperty("class", "row-detail")
        detail.setWordWrap(True)
        text.addWidget(detail)

        layout.addLayout(text, 1)

        # A small eye marks the rows that have a page to show.
        if row.preview is not None:
            layout.addWidget(icon_label("eye", MUTED_TEXT, 16), 0, Qt.AlignmentFlag.AlignTop)
            widget.setToolTip("")

        widget.setLayout(layout)
        return widget

    def _on_row_entered(self, widget):
        self._preview_row = widget
        self._preview_timer.start()

    def _show_preview(self):
        widget = self._preview_row
        if widget is not None and widget.row.preview is not None and widget.underMouse():
            self._preview_popup.show_beside(widget.row.preview, self, widget)

    def _hide_preview(self):
        self._preview_timer.stop()
        self._preview_row = None
        self._preview_popup.hide()

    def hideEvent(self, event):
        self._hide_preview()
        super().hideEvent(event)

    @staticmethod
    def _breakable(text):
        """Lets a long filename wrap at its separators -- a word-wrapped
        QLabel can't otherwise break inside a word, and would be clipped."""
        for separator in ("_", "-", ".", "/"):
            text = text.replace(separator, separator + "\u200b")
        return text

    def set_state(self, enabled, message, ready=False):
        """Build button enabled/disabled, with a one-line reason (or the
        green "Ready to build") under it."""
        self.build_button.setEnabled(enabled)
        self.reason_label.setText(message)
        self.reason_label.setProperty("class", "ok-text" if ready else "status")
        repolish(self.reason_label)

    def set_action(self, kind):
        """What the big button does right now: "build" (primary), "cancel"
        while a build runs, "rebuild" after a failed or cancelled one, or
        "new" once a report is finished."""
        text, icon_name, primary = {
            "build": ("Build report", "play", True),
            "cancel": ("Cancel", "x", False),
            # After a failure or cancel, Try again in the main area is the
            # primary action, so this one steps back to secondary.
            "rebuild": ("Build again", "play", False),
            # Once a report is done, Open report is the primary action.
            "new": ("Start new report", "refresh", False),
        }[kind]
        self.build_button.setText(text)
        self.build_button.setIcon(icon(icon_name, ON_ACCENT if primary else MUTED_TEXT, 16))
        self.build_button.setProperty("class", "primary" if primary else "")
        repolish(self.build_button)
        if kind != "build":
            self.build_button.setEnabled(True)
            self.reason_label.setText("")
