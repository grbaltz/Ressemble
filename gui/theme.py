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

QLineEdit:disabled, QDateEdit:disabled {{
    color: {MUTED_TEXT};
    background: {BACKGROUND};
}}

QLineEdit[readOnly="true"] {{
    background: {BACKGROUND};
    color: {MUTED_TEXT};
}}

QDateEdit::drop-down {{
    width: 0px;
    border: none;
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

QListWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px 6px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background: {BACKGROUND};
    color: {TEXT};
}}

QListWidget::item:hover {{
    background: {BACKGROUND};
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
