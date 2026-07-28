import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    print("Here is where I would fire assemble_report()")
    
    app = QApplication(sys.argv)

    window = MainWindow()  
    window.show()

    sys.exit(app.exec())
    # assemble_report()

if __name__ == "__main__":
    main()