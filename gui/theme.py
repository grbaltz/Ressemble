FONT_FAMILY = '"Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif'

BACKGROUND = "#F7F8FA"
SURFACE = "#FFFFFF"
BORDER = "#E1E4E8"
TEXT = "#1F2328"
MUTED_TEXT = "#6E7681"
ACCENT = "#ec9624"
ACCENT_HOVER = "#b6741d"
ACCENT_PRESSED = "#855415"
ACCENT_DISABLED = "#fdc479"
DANGER = "#D1453B"

STYLESHEET = f"""
QWidget {{
    background: {BACKGROUND};
    color: {TEXT};
    font-family: {FONT_FAMILY};
    font-size: 14px;
}}

QMainWindow {{
    background: {BACKGROUND};
}}

QLabel[class="title"] {{
    font-size: 22px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel[class="subtitle"] {{
    font-size: 14px;
    color: {MUTED_TEXT};
}}

QLabel[class="status"] {{
    font-size: 13px;
    color: {MUTED_TEXT};
}}

QLabel[class="warning"] {{
    font-size: 13px;
    color: {DANGER};
}}

QLabel[class="section"] {{
    font-size: 13px;
    font-weight: 600;
    color: {MUTED_TEXT};
    letter-spacing: 0.5px;
}}

QLineEdit, QDateEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
}}

QLineEdit:focus, QDateEdit:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit[dragActive="true"] {{
    border: 1px dashed {ACCENT};
    background: {BACKGROUND};
}}

QLineEdit:disabled, QDateEdit:disabled {{
    color: {MUTED_TEXT};
    background: {BACKGROUND};
}}

QLineEdit[readOnly="true"] {{
    background: {BACKGROUND};
    color: {MUTED_TEXT};
}}

/* No ::drop-down/::down-arrow rule here (deliberately) -- styling
   ::drop-down at all makes Qt stop drawing the style's own arrow glyph
   unless ::down-arrow supplies a replacement image, and a QSS
   border-triangle (the usual no-asset trick for this) rendered as a
   solid block, not a triangle, under this app's Fusion style: confirmed
   by rendering both this and QComboBox's drop-down and inspecting the
   pixels. Leaving both unstyled gets Fusion's own correctly-shaped arrow
   for free, with no icon asset needed. */

/* The calendar popup QDateEdit's now-enabled drop-down opens -- styled to match
   the rest of the app's theme rather than the OS default, since it's the
   one native Qt widget left in an otherwise custom-styled form. */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}

QCalendarWidget QToolButton {{
    color: {TEXT};
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: 600;
}}

QCalendarWidget QToolButton:hover {{
    background: {BACKGROUND};
}}

QCalendarWidget QToolButton::menu-indicator {{
    image: none;
}}

QCalendarWidget QSpinBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 2px 4px;
    selection-background-color: {ACCENT};
}}

QCalendarWidget QMenu {{
    background: {SURFACE};
    border: 1px solid {BORDER};
}}

QCalendarWidget QAbstractItemView {{
    background: {SURFACE};
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: white;
    outline: none;
}}

QCalendarWidget QAbstractItemView:disabled {{
    color: {MUTED_TEXT};
}}

QComboBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
}}

QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    outline: none;
    selection-background-color: {ACCENT};
}}

QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    color: {TEXT};
}}

QPushButton:hover {{
    border: 1px solid {ACCENT};
}}

QPushButton:pressed {{
    background: {BACKGROUND};
}}

QPushButton:disabled {{
    color: {MUTED_TEXT};
    border: 1px solid {BORDER};
    background: {BACKGROUND};
}}

QPushButton[class="primary"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: white;
    font-weight: 600;
    padding: 9px 22px;
}}

QPushButton[class="primary"]:hover {{
    background: {ACCENT_HOVER};
    border: 1px solid {ACCENT_HOVER};
}}

QPushButton[class="primary"]:pressed {{
    background: {ACCENT_PRESSED};
    border: 1px solid {ACCENT_PRESSED};
}}

QPushButton[class="primary"]:disabled {{
    background: {ACCENT_DISABLED};
    border: 1px solid {ACCENT_DISABLED};
    color: white;
}}

QPushButton[class="link"] {{
    background: transparent;
    border: none;
    color: {ACCENT};
    padding: 4px 2px;
    text-align: left;
}}

QPushButton[class="link"]:hover {{
    color: {ACCENT_HOVER};
    text-decoration: underline;
}}

QPushButton[class="toggle"] {{
    background: transparent;
    border: none;
    color: {MUTED_TEXT};
    padding: 4px 2px;
    text-align: left;
    font-size: 13px;
}}

QPushButton[class="toggle"]:hover {{
    color: {TEXT};
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {SURFACE};
}}

QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}

QProgressBar {{
    background: {BORDER};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 5px;
}}

QTextEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {MUTED_TEXT};
    font-family: "Consolas", "Menlo", monospace;
    font-size: 12px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


def apply_theme(app):
    app.setStyleSheet(STYLESHEET)
