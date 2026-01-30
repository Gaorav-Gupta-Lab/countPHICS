import sys
from pathlib import Path
from sys import platform
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QWidget, QTextEdit, QMessageBox, QHBoxLayout)
from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFont, QTextCursor

# Custom QSS Styling
STYLE_SHEET = """
QMainWindow {
    background-color: #2b2b2b;
}

QTextEdit {
    background-color: #121212;
    color: #a9b7c6;
    border: 1px solid #323232;
    border-radius: 4px;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
}

QPushButton {
    font-weight: bold;
    font-size: 14px;
    padding: 10px 20px;
    border-radius: 6px;
    color: white;
}

QPushButton#run_btn {
    background-color: #2d8a4e;
    border: 1px solid #3eaf68;
}

QPushButton#run_btn:hover {
    background-color: #3eaf68;
}

QPushButton#run_btn:pressed {
    background-color: #246d3e;
}

QPushButton#run_btn:disabled {
    background-color: #3c413e;
    color: #7d7d7d;
}

QPushButton#cancel_btn {
    background-color: #b33a3a;
    border: 1px solid #d44c4c;
}

QPushButton#cancel_btn:hover {
    background-color: #d44c4c;
}

QPushButton#cancel_btn:disabled {
    background-color: #4a3232;
    color: #7d7d7d;
}
"""

class FijiRunnerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Colony Counter Interface")
        self.resize(700, 500)
        self.setStyleSheet(STYLE_SHEET)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header/Console Label
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("System logs will appear here...")
        layout.addWidget(self.console)

        # Button Row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.run_btn = QPushButton("▶  LAUNCH FIJI")
        self.run_btn.setObjectName("run_btn")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.start_process)
        
        self.cancel_btn = QPushButton("✖  CANCEL")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_process)

        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setCentralWidget(main_widget)

    def get_command(self):
        current_dir = Path(__file__).parent.resolve()
        script_path = current_dir / "macro_moj.py"
        
        if platform == "win32":
            fiji_path = current_dir.parent / "ImageJ-win64.exe"
        else:
            fiji_path = Path("/Users/pguerra/Library/CloudStorage/OneDrive-UniversityofNorthCarolinaatChapelHill/Desktop/Fiji")

        if not fiji_path.exists():
            self.log_to_console(f"ERROR: Fiji not found at {fiji_path}", "red")
            return None

        return str(fiji_path), ["--console", "-macro", str(script_path)]

    def log_to_console(self, text, color="#a9b7c6"):
        self.console.moveCursor(QTextCursor.End)
        self.console.insertHtml(f"<span style='color: {color};'>{text}</span><br>")
        self.console.ensureCursorVisible()

    def start_process(self):
        cmd_info = self.get_command()
        if not cmd_info: return

        executable, args = cmd_info
        self.console.clear()
        self.log_to_console("<b>INITIALIZING SUBSYSTEM...</b>", "#5fb3b3")
        
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.process.start(executable, args)

    def cancel_process(self):
        if self.process.state() == QProcess.Running:
            self.log_to_console("<b>SIGNAL: Termination sent.</b>", "orange")
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.log_to_console(data.strip())

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.log_to_console(data.strip(), "#ff5d5d")

    def process_finished(self, exit_code, exit_status):
        color = "#5fb3b3" if exit_code == 0 else "#b6b6b6"
        self.log_to_console(f"<b>PROCESS FINISHED (Code: {exit_code})</b>", color)
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FijiRunnerGUI()
    window.show()
    sys.exit(app.exec())