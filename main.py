import sys
from PySide6.QtWidgets import QApplication
from src.paths import ensure_data_dirs
from gui.main_window import MainWindow
from gui.theme import apply_theme

def main():
    ensure_data_dirs()
    app = QApplication(sys.argv)
    apply_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()