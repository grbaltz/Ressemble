from PySide6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QCalendarWidget
from PySide6.QtCore import Qt, QDate, QPoint, Signal
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
        self._popup = None

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
        popup = QCalendarWidget()
        popup.setWindowFlags(Qt.WindowType.Popup)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setSelectedDate(self._date)
        popup.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        popup.clicked.connect(self._on_picked)
        popup.move(self.mapToGlobal(QPoint(0, self.height() + 2)))
        self._popup = popup
        popup.show()

    def _on_picked(self, date):
        self.setDate(date)
        if self._popup is not None:
            self._popup.close()
            self._popup = None
