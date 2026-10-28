from src.paths import BUNDLE_ROOT

FONT_FAMILY = '"Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif'

BACKGROUND = "#F4F5F7"
SURFACE = "#FFFFFF"
BORDER = "#DDE0E4"
BORDER_STRONG = "#C3C8CE"
TEXT = "#20242A"
MUTED_TEXT = "#69707A"
COMBO_ARROW = (BUNDLE_ROOT / "gui" / "assets" / "icons" / "chevron-down-muted.svg").as_posix()
CHARCOAL = "#2B2F36"
CHARCOAL_BORDER = "#525963"

ACCENT = "#EC9624"
ACCENT_HOVER = "#DB8710"
ACCENT_PRESSED = "#C27409"
ACCENT_TINT = "#FDF1DC"
ACCENT_TEXT = "#6B3F00"
ACCENT_LINK = "#9A5A00"
# Dark ink, not white, on the accent: white on #EC9624 is only ~2:1.
ON_ACCENT = "#20242A"

OK = "#2F7D4F"
OK_TINT = "#E4F3EA"
OK_DOT = "#4CC38A"
WARN_TEXT = "#7A4B05"
WARN_TINT = "#FFF1D2"
WARN_BORDER = "#F2D58A"
DANGER = "#D1453B"

STYLESHEET = f"""
/* Transparent by default so nothing paints a grey box inside a white card;
   only top-level surfaces get a real background below. */
QWidget {{
    background: transparent;
    color: {TEXT};
    font-family: {FONT_FAMILY};
    font-size: 14px;
}}

QMainWindow, QDialog {{
    background: {BACKGROUND};
}}

QToolTip {{
    background: {CHARCOAL};
    color: white;
    border: none;
    padding: 4px 8px;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QLabel[class="title"] {{
    font-size: 22px;
    font-weight: 600;
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

QLabel[class="ok-text"] {{
    font-size: 12px;
    color: {OK};
}}

QLabel[class="field-label"] {{
    font-size: 13px;
    color: {MUTED_TEXT};
}}

QLabel[class="card-title"] {{
    font-size: 15px;
    font-weight: 600;
}}

QLabel[class="row-title"] {{
    font-size: 14px;
    font-weight: 600;
}}

QLabel[class="row-detail"] {{
    font-size: 12px;
    color: {MUTED_TEXT};
}}

/* ---- Inputs ---- */

QLineEdit, QDateEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
    selection-color: {ON_ACCENT};
}}

QLineEdit:focus, QDateEdit:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit:disabled, QDateEdit:disabled {{
    color: {MUTED_TEXT};
    background: {BACKGROUND};
}}

QLineEdit[readOnly="true"] {{
    background: {BACKGROUND};
    color: {MUTED_TEXT};
}}

/* The drop-down arrow needs its own image once ::drop-down is styled
   (Qt stops drawing the style's glyph otherwise); a QSS border-triangle
   rendered as a solid block here, so a small SVG file stands in. */

QCalendarWidget {{
    background: {SURFACE};
}}

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
    selection-color: {ON_ACCENT};
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

QComboBox::drop-down, QDateEdit::drop-down {{
    border: none;
    width: 28px;
}}

QComboBox::down-arrow, QDateEdit::down-arrow {{
    image: url({COMBO_ARROW});
    width: 14px;
    height: 14px;
}}

QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox:disabled {{
    color: {MUTED_TEXT};
    background: {BACKGROUND};
}}

QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    outline: none;
    selection-background-color: {ACCENT_TINT};
    selection-color: {ACCENT_TEXT};
}}

/* ---- Buttons ---- */

QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 7px 14px;
    color: {TEXT};
}}

QPushButton:hover {{
    border: 1px solid {ACCENT};
}}

QPushButton:pressed {{
    background: {BACKGROUND};
}}

QPushButton:focus {{
    border: 1px solid {ACCENT};
}}

QPushButton:disabled {{
    color: {MUTED_TEXT};
    border: 1px solid {BORDER};
    background: {BACKGROUND};
}}

QPushButton[class="primary"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: {ON_ACCENT};
    font-weight: 600;
    padding: 10px 22px;
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
    background: {BORDER};
    border: 1px solid {BORDER};
    color: {MUTED_TEXT};
}}

QPushButton[class="link"] {{
    background: transparent;
    border: none;
    color: {ACCENT_LINK};
    font-weight: 600;
    padding: 4px 2px;
    text-align: left;
}}

QPushButton[class="link"]:hover {{
    color: {ACCENT_PRESSED};
    text-decoration: underline;
}}

QPushButton[class="link"]:focus {{
    border: none;
    text-decoration: underline;
}}

QPushButton[class="link"]:disabled {{
    background: transparent;
    border: none;
    color: {MUTED_TEXT};
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
    border: none;
}}

QPushButton[class="toggle"]:focus {{
    border: none;
    color: {TEXT};
}}

QPushButton[class="icon-button"] {{
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
}}

QPushButton[class="icon-button"]:hover {{
    background: {BACKGROUND};
    border: none;
}}

QPushButton[class="segment"] {{
    background: {SURFACE};
    border: none;
    border-radius: 0;
    color: {MUTED_TEXT};
    padding: 7px 14px;
    font-size: 13px;
}}

QPushButton[class="segment"]:hover {{
    color: {TEXT};
    border: none;
}}

QPushButton[class="segment"]:checked {{
    background: {ACCENT_TINT};
    color: {ACCENT_TEXT};
}}

QFrame[class="segmented"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

QPushButton[class="header-button"] {{
    background: transparent;
    border: 1px solid {CHARCOAL_BORDER};
    border-radius: 6px;
    color: #E6E8EB;
    padding: 6px 12px;
    font-size: 13px;
}}

QPushButton[class="header-button"]:hover {{
    border: 1px solid {ACCENT};
    color: white;
}}

QPushButton[class="header-button"]:focus {{
    border: 1px solid {ACCENT};
}}

/* ---- Frames and chrome ---- */

QFrame[class="header"] {{
    background: {CHARCOAL};
}}

QLabel[class="header-title"] {{
    color: white;
    font-size: 16px;
    font-weight: 600;
}}

QLabel[class="logo-mark"] {{
    background: {ACCENT};
    border-radius: 7px;
}}

QLabel[class="dot"] {{
    border-radius: 4px;
    background: {OK_DOT};
}}

QLabel[class="dot"][state="warn"] {{
    background: {ACCENT};
}}

QLabel[class="dot"][state="busy"] {{
    background: {BORDER_STRONG};
}}

QFrame[class="card"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QLabel[class="badge"] {{
    background: {CHARCOAL};
    color: white;
    border-radius: 11px;
    font-size: 12px;
    font-weight: 600;
}}

QLabel[class="badge"][state="done"] {{
    background: {OK_TINT};
}}

QLabel[class="done-mark"] {{
    background: {OK_TINT};
    border-radius: 32px;
}}

QLabel[class="icon-tile"] {{
    background: {ACCENT_TINT};
    border-radius: 8px;
}}

QFrame[class="card"][dragActive="true"] {{
    background: {ACCENT_TINT};
    border: 1px dashed {ACCENT};
}}

QLabel[class="chip"] {{
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 12px;
    font-weight: 600;
    background: {OK_TINT};
    color: {OK};
}}

QLabel[class="chip"][state="warn"] {{
    background: {WARN_TINT};
    color: {WARN_TEXT};
}}

QLabel[class="chip"][state="busy"] {{
    background: {BACKGROUND};
    color: {MUTED_TEXT};
}}

QFrame[class="banner"] {{
    background: {WARN_TINT};
    border: 1px solid {WARN_BORDER};
    border-radius: 8px;
}}

QFrame[class="banner"] QLabel {{
    color: {WARN_TEXT};
}}

QLabel[class="banner-text"] {{
    background: {WARN_TINT};
    border: 1px solid {WARN_BORDER};
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    color: {WARN_TEXT};
}}

QFrame[class="banner-ok"] {{
    background: {OK_TINT};
    border: 1px solid {OK_TINT};
    border-radius: 8px;
}}

QFrame[class="source-row"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

QFrame[class="source-row"][empty="true"] {{
    background: {BACKGROUND};
    border: 1px dashed {BORDER_STRONG};
}}

QFrame[class="source-row"][dragActive="true"] {{
    background: {ACCENT_TINT};
    border: 1px dashed {ACCENT};
}}

QFrame[class="preview-popup"] {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
}}

QPushButton[class="field-button"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 0;
    text-align: left;
}}

QPushButton[class="field-button"]:hover, QPushButton[class="field-button"]:focus {{
    border: 1px solid {ACCENT};
}}

QFrame[class="divider"] {{
    background: {BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER_STRONG};
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
    background: #23272D;
    border: none;
    border-radius: 6px;
    color: #B9BFC8;
    padding: 6px 8px;
    font-family: "Consolas", "Menlo", monospace;
    font-size: 12px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


def apply_theme(app):
    app.setStyleSheet(STYLESHEET)


def repolish(widget):
    """Re-evaluates the stylesheet after a dynamic property changed on a
    widget that's already shown -- Qt doesn't do this on its own."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
