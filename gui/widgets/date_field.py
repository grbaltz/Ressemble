from PySide6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QCalendarWidget
from PySide6.QtCore import Qt, QDate, QPoint, QTimer, Signal
from gui.icons import icon_label
from gui.theme import MUTED_TEXT


class DateField(QPushButton):
    """A date shown in a field that opens a calendar when clicked anywhere
    on it. (A QDateEdit only opens its calendar from the small arrow at
    its edge; clicking the text just edits it, which isn't what anyone
    expects from a date picker.)"""

    dateChanged = Signal(QDate)

    DISPLAY_FORMAT = "MMMM d, yyyy"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "field-button")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._date = QDate.currentDate()

        # One calendar for the field's whole life, owned by the field and
        # only ever shown and hidden. Creating and deleting it per pick
        # destroyed it from inside its own `clicked` signal, which crashes
        # on macOS.
        self._popup = QCalendarWidget(self)
        self._popup.setWindowFlags(Qt.WindowType.Popup)
        self._popup.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._popup.clicked.connect(self._on_picked)

        # The label and icon sit on top of the button, so they must not
        # swallow clicks meant for it.
        self._text = QLabel()
        self._text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        calendar = icon_label("calendar", MUTED_TEXT, 16)
        calendar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        layout.addWidget(self._text, 1)
        layout.addWidget(calendar)
        self.setLayout(layout)
        self.setMinimumHeight(36)

        self.clicked.connect(self._open_calendar)
        self._show_date()

    def date(self):
        return self._date

    def setDate(self, date):
        if date == self._date:
            return
        self._date = date
        self._show_date()
        self.dateChanged.emit(date)

    def _show_date(self):
        self._text.setText(self._date.toString(self.DISPLAY_FORMAT))

    def _open_calendar(self):
        self._popup.setSelectedDate(self._date)
        self._popup.move(self.mapToGlobal(QPoint(0, self.height() + 2)))
        self._popup.show()

    def _on_picked(self, date):
        self.setDate(date)
        # After the signal has returned, not during it.
        QTimer.singleShot(0, self._popup.hide)
