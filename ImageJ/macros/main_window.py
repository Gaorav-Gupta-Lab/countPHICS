import sys
from pathlib import Path
from sys import platform
import datetime
import matplotlib.pyplot as plt
import natsort

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QWidget, QTextEdit, QHBoxLayout,
                             QFileDialog, QCheckBox, QSpinBox, QGroupBox, 
                             QDoubleSpinBox, QLineEdit, QLabel, QGridLayout)

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QTextCursor

from grapher import FIJIGrapher

# Custom QSS Styling
STYLE_SHEET = """
/* --- App base --- */
QMainWindow {
    background-color: #23262b;
}

QWidget {
    color: #e6e6e6;
    font-size: 12px;
}

/* --- Title label --- */
QLabel#title {
    font-size: 20px;
    font-weight: 700;
    color: #f0f0f0;
}

/* --- Cards / group boxes --- */
QGroupBox {
    background-color: #2b2f36;
    border: 1px solid #3a3f47;
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px;
    font: bold;
    color: #5fb3b3;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    margin-left: 2px;
}

/* --- Inputs --- */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1c1f24;
    border: 1px solid #3a3f47;
    border-radius: 8px;
    padding: 6px 12px;
    color: #e6e6e6;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #5fb3b3;
}

QLineEdit::placeholder {
    color: #8e96a3;
}

/* Make spinboxes look cleaner */
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 16px;
    border: none;
    background: transparent;
}

/* --- Checkboxes --- */
QCheckBox {
    spacing: 6px;
    padding: 1px 0;
    color: #dfe4ea;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1px solid #5b616c;
    background-color: #1c1f24;
}

QCheckBox::indicator:hover {
    border: 1px solid #7faeb3;
}

QCheckBox::indicator:checked {
    background-color: #5fb3b3;
    border: 1px solid #5fb3b3;
}

QCheckBox::indicator:checked:hover {
    background-color: #6fd0d0;
}

/* --- Console --- */
QTextEdit {
    background-color: #111316;
    color: #cbd5e1;
    border: 1px solid #3a3f47;
    border-radius: 10px;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
}

QTextEdit:focus {
    border: 1px solid #5fb3b3;
}

/* --- Buttons --- */
QPushButton {
    font-weight: 700;
    font-size: 13px;
    padding: 10px 16px;
    border-radius: 10px;
    color: white;
    border: 1px solid transparent;
}

QPushButton:hover {
    opacity: 0.95;
}

QPushButton:pressed {
    opacity: 0.88;
}

/* Primary */
QPushButton#run_btn {
    background-color: #2d8a4e;
    border: 1px solid #3eaf68;
}

QPushButton#run_btn:hover { background-color: #39a760; }
QPushButton#run_btn:pressed { background-color: #257242; }
QPushButton#run_btn:disabled {
    background-color: #39413d;
    border: 1px solid #39413d;
    color: #8a8f96;
}

/* Danger */
QPushButton#cancel_btn {
    background-color: #b33a3a;
    border: 1px solid #d44c4c;
}

QPushButton#cancel_btn:hover { background-color: #d44c4c; }
QPushButton#cancel_btn:pressed { background-color: #952f2f; }
QPushButton#cancel_btn:disabled {
    background-color: #3e2f2f;
    border: 1px solid #3e2f2f;
    color: #8a8f96;
}

/* Neutral */
QPushButton#exit_btn {
    background-color: #3c4048;
    border: 1px solid #515763;
}

QPushButton#exit_btn:hover { background-color: #515763; }
QPushButton#exit_btn:pressed { background-color: #2f333a; }

/* Smaller “browse” buttons */
QPushButton#browse_btn {
    padding: 6px 6px;
    font-weight: 600;
    background-color: #357575;
    border: 1px solid #515763;
    min-width: 90px;
    max-width: 95px;
    min-height: 20px;
    
}

QPushButton#browse_btn:hover { background-color: #316363; }
QPushButton#browse_btn:pressed { background-color: #3f434a; }
"""

class FijiRunnerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Colony Counter Interface")
        self.resize(1000, 800)
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
        self.input_btn = QPushButton("Browse Input")
        self.input_btn.setObjectName("browse_btn")
        self.input_btn.clicked.connect(self.select_input_file)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Input image:"))
        row1.addWidget(self.input_edit)
        row1.addWidget(self.input_btn)
        layout.addLayout(row1)

        # Output path
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output directory… (will default to input image folder if left blank)")
        self.output_btn = QPushButton("Browse Output")
        self.output_btn.setObjectName("browse_btn")
        self.output_btn.clicked.connect(self.select_output_folder)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output folder:"))
        row2.addWidget(self.output_edit)
        row2.addWidget(self.output_btn)
        layout.addLayout(row2)

        # ---- General settings ----
        general_box = QGroupBox("General settings")
        general_layout = QVBoxLayout()

        self.chk_auto_thresh = QCheckBox("Automatic threshold (UNSTABLE; Not Recommended)")
        self.chk_same_roi = QCheckBox("Use same ROI for all images", checked=True)
        self.chk_six_well = QCheckBox("6-well plate analysis")
        self.chk_advanced = QCheckBox("Enable advanced settings")

        general_layout.addWidget(self.chk_auto_thresh)
        general_layout.addWidget(self.chk_same_roi)
        general_layout.addWidget(self.chk_six_well)
        general_layout.addWidget(self.chk_advanced)

        general_box.setLayout(general_layout)
        layout.addWidget(general_box)

        # ---- Advanced settings ----
        advanced_box = QGroupBox("Advanced Settings")
        advanced_layout = QGridLayout()

        self.spin_rolling = QSpinBox()
        self.spin_rolling.setRange(1, 10000)
        self.spin_rolling.setValue(62)
        label_rolling_radius = QLabel("Rolling Ball Radius:")

        self.spin_min_col = QSpinBox()
        self.spin_min_col.setRange(1, 100000)
        self.spin_min_col.setValue(150)
        label_min_col_size = QLabel("Min Colony Size:")

        self.spin_max_col = QSpinBox()
        self.spin_max_col.setRange(1, 1000000)
        self.spin_max_col.setValue(10000)
        label_max_col_size = QLabel("Max Colony Size:")

        self.spin_circ = QDoubleSpinBox()
        self.spin_circ.setRange(0.0, 1.0)
        self.spin_circ.setSingleStep(0.05)
        self.spin_circ.setValue(0.5)
        label_circularity = QLabel("Min Circularity:")

        self.spin_sigma = QDoubleSpinBox()
        self.spin_sigma.setRange(0.0, 100.0)
        self.spin_sigma.setValue(2.0)
        label_sigma = QLabel("Sigma:")

        for spin in (
            self.spin_rolling,
            self.spin_min_col,
            self.spin_max_col,
            self.spin_circ,
            self.spin_sigma,
        ):
            spin.setFixedWidth(120)

        for label in (
            label_rolling_radius,
            label_min_col_size,
            label_max_col_size,
            label_circularity,
            label_sigma,
        ):
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.spin_rolling.setToolTip("Radius for rolling ball background noise subtraction.")
        self.spin_min_col.setToolTip("Minimum colony size (in pixels) to be counted.")
        self.spin_max_col.setToolTip("Maximum colony size (in pixels) to be counted.")
        self.spin_circ.setToolTip("Minimum circularity (0.0 - 1.0) for colony detection.")
        self.spin_sigma.setToolTip("Sigma value for Gaussian blur applied before colony detection.")

        advanced_layout.setColumnStretch(0, 0)  # label (left)
        advanced_layout.setColumnStretch(1, 0)  # spinbox (left)

        advanced_layout.setColumnStretch(2, 1)  # empty space
        # advanced_layout.setColumnStretch(3, 1)  # empty space
        advanced_layout.setColumnStretch(4, 1)  # empty space

        advanced_layout.setColumnStretch(5, 0)  # label (right)
        advanced_layout.setColumnStretch(6, 0)  # spinbox (right)

        advanced_layout.addWidget(label_rolling_radius, 0, 0); advanced_layout.addWidget(self.spin_rolling, 0, 1)
        advanced_layout.addWidget(label_min_col_size, 0, 2); advanced_layout.addWidget(self.spin_min_col, 0, 3)
        advanced_layout.addWidget(label_max_col_size, 0, 4); advanced_layout.addWidget(self.spin_max_col, 0, 5)
        advanced_layout.addWidget(label_circularity, 1, 0); advanced_layout.addWidget(self.spin_circ, 1, 1)
        advanced_layout.addWidget(label_sigma, 1, 2); advanced_layout.addWidget(self.spin_sigma, 1, 3)

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
        # always precede printed line with datetime stamp
        self.console.insertHtml(f"<span style='color: {color};'>[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}</span><br>")
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
        ]


        if self.chk_advanced.isChecked():
            lines.extend([
                "rolling_ball=" + str(self.spin_rolling.value()),
                "min_colony=" + str(self.spin_min_col.value()),
                "max_colony=" + str(self.spin_max_col.value()),
                "circularity=" + str(self.spin_circ.value()),
                "sigma=" + str(self.spin_sigma.value()),
            ])

        image_files = [
            str(file)
            for file in input_path.parent.iterdir()
            if file.suffix.lower() in [".tif", ".tiff"]
        ]
        image_files = natsort.natsorted(image_files)
        lines.append("images=" + ";".join(image_files))

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
                self.log_to_console(line.strip(), "#eeec62")

    def process_finished(self, exit_code, exit_status):
        color = "#5fb3b3" if exit_code == 0 else "#b6b6b6"
        self.log_to_console(f"<b>PROCESS FINISHED (Code: {exit_code})</b>", color)
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.on_fiji_finished(
            summary_file=self.get_output_path(self.get_input_path()) / "Summary.txt",
            area_distribution_files=[file for file in Path(self.get_output_path(self.get_input_path()), "size_distribution_files").glob("*size_distribution.txt")],
            output_dir=self.get_output_path(self.get_input_path())
        )

    def on_fiji_finished(self, summary_file: Path, area_distribution_files: list[Path], output_dir: Path):
        try:
            grapher = FIJIGrapher()

            plots_dir = output_dir / "plots"
            plots_dir.mkdir(exist_ok=True)

            # Generate boxplot for colony counts
            grapher.load_summary_file(summary_file)
            grapher.boxplot(
                x="Group",
                y="Num colonies",
                title="Mean intensity by condition"
            )
            grapher.save_current_plot(plots_dir / "all_colony_counts_boxplot.png")
            plt.close()

            # Generate histograms for each area distribution file
            for area_distribution_file in area_distribution_files:
                area_distribution_data = grapher.load_area_distribution_file(
                    area_distribution_file, skiprows=1
                )
                grapher.histogram(
                    x=area_distribution_data.columns.tolist()[0],
                    bins=30,
                    title="Colony Area Distribution"
                )
                grapher.save_current_plot(plots_dir / f"{area_distribution_file.stem}_area_hist.png")
                plt.close()

            self.log_to_console(
                f"Saved plots to {plots_dir}", "green"
            )

        except Exception as e:
            self.log_to_console(
                f"Plot generation failed: {e}", "red"
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FijiRunnerGUI()
    window.show()
    sys.exit(app.exec())