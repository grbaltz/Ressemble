from PySide6.QtWidgets import QLabel, QDialog, QPushButton, QProgressBar, QTextEdit, QGridLayout, QWidget, QVBoxLayout, QLineEdit, QCheckBox, QHBoxLayout
from PySide6.QtCore import Qt, QThread, QSettings
from pathlib import Path
from gui.workers.assemble_worker import AssembleWorker

class AssembleScreen(QWidget):
    def __init__(self, main_window, settings):
        super().__init__()
        self.main_window = main_window
        self.settings = settings
        self._client_name = ""
        self._enrolled = False

        # Title
        self.title = QLabel("Generate Report")

        self.assemble_button = QPushButton("Assemble Report")
        self.assemble_button.clicked.connect(self.assemble)

        # Client Name
        self.name_label = QLabel("Enter client name:")
        self.client_name = QLineEdit()
        self.client_name.setMaximumWidth(300)
        self.client_name.textChanged.connect(self.save_name)

        # Enroll in Plan360 / Enrolled
        self.enroll = QCheckBox("Enrolled with View360?")
        self.enroll.stateChanged.connect(self.save_enroll_state)

        # Progress
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMinimum(0)
        self.progress.setMaximum(16)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        # --- Layout ---
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignHCenter)

        # Name row: label + input, centered as a unit
        name_row = QHBoxLayout()
        name_row.addStretch(1)
        name_row.addWidget(self.name_label)
        name_row.addWidget(self.client_name)
        name_row.addStretch(1)
        main_layout.addLayout(name_row)

        # Checkbox row, centered
        enroll_row = QHBoxLayout()
        enroll_row.addStretch(1)
        enroll_row.addWidget(self.enroll)
        enroll_row.addStretch(1)
        main_layout.addLayout(enroll_row)

        # Equal stretch above/below the button pushes it to the
        # vertical midpoint of the remaining space
        main_layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.assemble_button)
        button_row.addStretch(1)
        main_layout.addLayout(button_row)

        main_layout.addStretch(1)

        self.setLayout(main_layout)
        
    def assemble(self):
        self.thread = QThread()

        result = self.main_window.scan_results
        
        self.worker = AssembleWorker(
            matched_pages=result["matched_pages"],
            sources=result["sources"],
            advisors_file=result["advisors_file"],
            client_name=self._client_name,
            enrolled=self._enrolled
        )
        
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)
        # self.worker.request_advisors.connect(self.request_advisors)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    def save_name(self, name):
        self._client_name = name
        self.name_label = name

    def save_enroll_state(self, state):
        self._enrolled = bool(state)