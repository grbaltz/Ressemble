import multiprocessing
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.paths import ensure_data_dirs, ICON_PATH
from gui.main_window import MainWindow
from gui.theme import apply_theme

def main():
    ensure_data_dirs()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    apply_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    # Report assembly runs in a child process (see AssembleWorker); in a
    # PyInstaller build that child re-launches this executable, and
    # freeze_support() is what routes it to the worker instead of the GUI.
    multiprocessing.freeze_support()
    main()