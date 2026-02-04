import sys
from pathlib import Path
from sys import platform
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QWidget, QTextEdit, QHBoxLayout,
                             QFileDialog, QCheckBox, QSpinBox, QGroupBox, 
                             QDoubleSpinBox, QLineEdit, QLabel)

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QTextCursor

# import json, tempfile

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

QPushButton#exit_btn {
    background-color: #555555;
    border: 1px solid #777777;
}

QPushButton#exit_btn:hover {
    background-color: #777777;
}
"""

class FijiRunnerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Colony Counter Interface")
        self.resize(900, 600)
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

        # Input path
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Select first image…")
        input_btn = QPushButton("Browse Image")
        input_btn.clicked.connect(self.select_input_file)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Input image:"))
        row1.addWidget(self.input_edit)
        row1.addWidget(input_btn)
        layout.addLayout(row1)

        # Output path
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output directory… (will default to input image folder if left blank)")
        output_btn = QPushButton("Browse Folder")
        output_btn.clicked.connect(self.select_output_folder)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output folder:"))
        row2.addWidget(self.output_edit)
        row2.addWidget(output_btn)
        layout.addLayout(row2)

        # ---- General settings ----
        general_box = QGroupBox("Analysis settings")
        general_layout = QVBoxLayout()

        self.chk_auto_thresh = QCheckBox("Automatic threshold (UNSTABLE; Not Recommended)")
        self.chk_same_roi = QCheckBox("Use same ROI for all images")
        self.chk_six_well = QCheckBox("6-well plate analysis")
        self.chk_advanced = QCheckBox("Enable advanced settings")

        self.spin_last_image = QSpinBox()
        self.spin_last_image.setMinimum(1)
        self.spin_last_image.setMaximum(9999)
        self.spin_last_image.setValue(1)
        self.spin_last_image.setPrefix("Last image #: ")

        general_layout.addWidget(self.chk_auto_thresh)
        general_layout.addWidget(self.chk_same_roi)
        general_layout.addWidget(self.chk_six_well)
        general_layout.addWidget(self.chk_advanced)
        general_layout.addWidget(self.spin_last_image)

        general_box.setLayout(general_layout)
        layout.addWidget(general_box)

        # ---- Advanced settings ----
        advanced_box = QGroupBox("Advanced parameters")
        advanced_layout = QVBoxLayout()

        self.spin_rolling = QSpinBox()
        self.spin_rolling.setRange(1, 10000)
        self.spin_rolling.setValue(35)
        self.spin_rolling.setPrefix("Rolling ball: ")

        self.spin_min_col = QSpinBox()
        self.spin_min_col.setRange(1, 100000)
        self.spin_min_col.setValue(100)
        self.spin_min_col.setPrefix("Min colony size: ")

        self.spin_max_col = QSpinBox()
        self.spin_max_col.setRange(1, 1000000)
        self.spin_max_col.setValue(10000)
        self.spin_max_col.setPrefix("Max colony size: ")

        self.spin_circ = QDoubleSpinBox()
        self.spin_circ.setRange(0.0, 1.0)
        self.spin_circ.setSingleStep(0.05)
        self.spin_circ.setValue(0.5)
        self.spin_circ.setPrefix("Circularity: ")

        self.spin_sigma = QDoubleSpinBox()
        self.spin_sigma.setRange(0.0, 100.0)
        self.spin_sigma.setValue(2.0)
        self.spin_sigma.setPrefix("Sigma: ")

        advanced_layout.addWidget(self.spin_rolling)
        advanced_layout.addWidget(self.spin_min_col)
        advanced_layout.addWidget(self.spin_max_col)
        advanced_layout.addWidget(self.spin_circ)
        advanced_layout.addWidget(self.spin_sigma)

        advanced_box.setLayout(advanced_layout)
        advanced_box.setVisible(False)
        layout.addWidget(advanced_box)

        self.chk_advanced.toggled.connect(advanced_box.setVisible)

        # Button Row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.run_btn = QPushButton("▶ LAUNCH FIJI")
        self.run_btn.setObjectName("run_btn")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.start_process)
        
        self.cancel_btn = QPushButton("CANCEL PROCESS")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_process)

        self.exit_btn = QPushButton("✖ EXIT")
        self.exit_btn.setObjectName("exit_btn")
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.clicked.connect(self.close)

        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.exit_btn)
        
        layout.addLayout(button_layout)
        self.setCentralWidget(main_widget)

    def select_input_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select First Image")
        if f:
            self.input_edit.setText(f)

    def select_output_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self.output_edit.setText(d)


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

    def get_input_path(self):
        text = self.input_edit.text().strip()
        if not text:
            self.log_to_console("ERROR: Input image path is required.", "red")
            return None

        path = Path(text).resolve()
        if not path.exists():
            self.log_to_console(f"ERROR: Input file does not exist: {path}", "red")
            return None

        return path
    
    def get_output_path(self, input_path):
        text = self.output_edit.text().strip()

        if text:
            base = Path(text)
        else:
            base = input_path.parent
            self.output_edit.setText(str(base))

        output_path = (base / "countPHICS_output").resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        return output_path

    def write_config(self, input_path, output_path):
        config_path = output_path / "countPHICS_params.txt"

        lines = [
            "input=" + str(input_path),
            "output=" + str(output_path),

            "auto_threshold=" + str(self.chk_auto_thresh.isChecked()).lower(),
            "same_roi=" + str(self.chk_same_roi.isChecked()).lower(),
            "six_well=" + str(self.chk_six_well.isChecked()).lower(),
            "advanced=" + str(self.chk_advanced.isChecked()).lower(),
            "last_image=" + str(self.spin_last_image.value()),
        ]

        if self.chk_advanced.isChecked():
            lines.extend([
                "rolling_ball=" + str(self.spin_rolling.value()),
                "min_colony=" + str(self.spin_min_col.value()),
                "max_colony=" + str(self.spin_max_col.value()),
                "circularity=" + str(self.spin_circ.value()),
                "sigma=" + str(self.spin_sigma.value()),
            ])

        with open(config_path, "w") as f:
            f.write("\n".join(lines))

        self.log_to_console(f"Config written to {config_path}", "green")
        return config_path

    def launch_fiji(self):
        cmd_info = self.get_command()
        if not cmd_info:
            return

        executable, args = cmd_info

        # self.console.clear()
        self.log_to_console("<b>INITIALIZING SUBSYSTEM...</b>", "#5fb3b3")

        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.process.start(executable, args)

    def start_process(self):
        input_path = self.get_input_path()
        if not input_path:
            return

        output_path = self.get_output_path(input_path)
        self.write_config(input_path, output_path)

        self.launch_fiji()

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
        
        # List of "noisy" keywords to ignore
        junk_keywords = [
            "net.imagej", 
            "java.net",
            "java.lang",
            "java.rmi",
            "javassist",
            "org.scijava",
            "sun.reflect",
            "sun.rmi"
        ]
        
        for line in data.splitlines():
            # Only log the line if NONE of the junk keywords are in it
            if not any(key in line for key in junk_keywords):
                self.log_to_console(line.strip(), "#eeec62") # Red for real errors

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