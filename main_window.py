"""
This is the entry point for countPHICS2
"""

import sys
import os
from pathlib import Path
from sys import platform
import datetime
import matplotlib.pyplot as plt
import natsort

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QHBoxLayout,
                               QFileDialog, QCheckBox, QSpinBox, QGroupBox, QDoubleSpinBox, QLineEdit, QLabel,
                               QGridLayout)

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QTextCursor, QIcon
from ImageJ.macros.grapher import FIJIGrapher

class FijiRunnerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Colony Counter Interface")
        self.resize(1000, 800)
        # self.setStyleSheet(STYLE_SHEET)
        self.setStyleSheet(self.load_stylesheet())
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.console = QTextEdit()

        self.input_edit = QLineEdit()
        self.input_btn = QPushButton("Browse Input")
        self.output_edit = QLineEdit()
        self.output_btn = QPushButton("Browse Output")

        self.run_btn = QPushButton("▶ LAUNCH FIJI")
        self.cancel_btn = QPushButton("CANCEL PROCESS")
        self.exit_btn = QPushButton("✖ EXIT")
        
        # self.chk_auto_thresh = QCheckBox("Automatic threshold (UNSTABLE; Not Recommended)")
        self.chk_same_roi = QCheckBox("Use same ROI for all images", checked=True)
        self.chk_six_well = QCheckBox("6-well plate analysis")
        self.chk_plotting = QCheckBox("Generate plots after processing", checked=True)
        self.chk_advanced = QCheckBox("Enable advanced settings")

        self.spin_rolling = QSpinBox()
        self.spin_min_col = QSpinBox()
        self.spin_max_col = QSpinBox()
        self.spin_circ = QDoubleSpinBox()
        self.spin_sigma = QDoubleSpinBox()
        self.spin_roi_thickness = QSpinBox()


        self.init_ui()

    @staticmethod
    def load_stylesheet():
        """Loads a QSS file and returns its content."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        layout_file = os.path.join(base_dir, "layout.qss")

        try:
            with open(layout_file, 'r', encoding="utf-8-sig", newline="") as f:
                return f.read()

        except UnicodeDecodeError as e:
            print(f"Error: Could not decode stylesheet '{layout_file}' as UTF-8 ({e}).")
            print("Tip: Re-save layout.qss as UTF-8, or remove any unusual characters.")
            # Fallback: load with a Windows-friendly encoding so the app can still start
            with open(layout_file, "r", encoding="cp1252", errors="replace", newline="") as f:
                return f.read()

        except FileNotFoundError:
            print("Error: Stylesheet file {} not found.".format(layout_file))
            return ""

    def init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header/Console Label
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("System logs will appear here...")
        layout.addWidget(self.console)

        # Input path
        # self.input_edit.setPlaceholderText("Select first image…")
        self.input_edit.setPlaceholderText("Select Folder Containing Images")
        self.input_btn.setObjectName("browse_btn")
        self.input_btn.clicked.connect(self.select_input_folder)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Input image:"))
        row1.addWidget(self.input_edit)
        row1.addWidget(self.input_btn)
        layout.addLayout(row1)

        # Output path
        self.output_edit.setPlaceholderText("Select output directory… (will default to input image folder if left blank)")
        self.output_btn.setObjectName("browse_btn")
        self.output_btn.clicked.connect(self.select_output_folder)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output folder:"))
        row2.addWidget(self.output_edit)
        row2.addWidget(self.output_btn)
        layout.addLayout(row2)

        # ---- Settings container (horizontal) ----
        settings_container = QHBoxLayout()
        
        # ---- General settings ----
        general_box = QGroupBox("General settings")
        general_layout = QVBoxLayout()

        # general_layout.addWidget(self.chk_auto_thresh)
        general_layout.addWidget(self.chk_same_roi)
        general_layout.addWidget(self.chk_six_well)
        general_layout.addWidget(self.chk_plotting)
        general_layout.addWidget(self.chk_advanced)

        general_box.setLayout(general_layout)
        settings_container.addWidget(general_box)

        # ---- Advanced settings ----
        advanced_box = QGroupBox("Advanced Settings")
        advanced_layout = QGridLayout()

        self.spin_rolling.setRange(1, 10000)
        self.spin_rolling.setValue(62)
        label_rolling_radius = QLabel("Rolling Ball Radius:")


        self.spin_min_col.setRange(1, 100000)
        self.spin_min_col.setValue(150)
        label_min_col_size = QLabel("Min Colony Size:")

        self.spin_max_col.setRange(1, 1000000)
        self.spin_max_col.setValue(10000)
        label_max_col_size = QLabel("Max Colony Size:")

        self.spin_circ.setRange(0.0, 1.0)
        self.spin_circ.setSingleStep(0.05)
        self.spin_circ.setValue(0.5)
        label_circularity = QLabel("Min Circularity:")

        self.spin_sigma.setRange(0.0, 100.0)
        self.spin_sigma.setValue(2.0)
        label_sigma = QLabel("Sigma:")

        self.spin_roi_thickness.setRange(1, 20)
        self.spin_roi_thickness.setValue(3)
        label_roi_thickness = QLabel("ROI Thickness:")

        for spin in (
            self.spin_rolling,
            self.spin_min_col,
            self.spin_max_col,
            self.spin_circ,
            self.spin_sigma,
            self.spin_roi_thickness
        ):
            spin.setFixedWidth(120)

        for label in (
            label_rolling_radius,
            label_min_col_size,
            label_max_col_size,
            label_circularity,
            label_sigma,
            label_roi_thickness
        ):
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.spin_rolling.setToolTip("Radius for rolling ball background noise subtraction.")
        self.spin_min_col.setToolTip("Minimum colony size (in pixels) to be counted.")
        self.spin_max_col.setToolTip("Maximum colony size (in pixels) to be counted.")
        self.spin_circ.setToolTip("Minimum circularity (0.0 - 1.0) for colony detection.")
        self.spin_sigma.setToolTip("Sigma value for Gaussian blur applied before colony detection.")
        self.spin_roi_thickness.setToolTip("Thickness of the ROI border drawn around detected colonies.")

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
        advanced_layout.addWidget(label_roi_thickness, 1, 4); advanced_layout.addWidget(self.spin_roi_thickness, 1, 5)

        advanced_box.setLayout(advanced_layout)
        advanced_box.setVisible(False)
        settings_container.addWidget(advanced_box)
        
        # Add the horizontal settings container to the main layout
        layout.addLayout(settings_container)

        self.chk_advanced.toggled.connect(advanced_box.setVisible)

        # Button Row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.run_btn.setObjectName("run_btn")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.start_process)

        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_process)


        self.exit_btn.setObjectName("exit_btn")
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.clicked.connect(self.close)

        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.exit_btn)
        
        layout.addLayout(button_layout)
        self.setCentralWidget(main_widget)

    def select_input_folder(self):
        """
        f, _ = QFileDialog.getOpenFileName(self, "Select First Image")
        if f:
            self.input_edit.setText(f)
        """
        file_input_folder = QFileDialog.getExistingDirectory(self, "Select File Input Folder")
        if file_input_folder:
            self.input_edit.setText(file_input_folder)

    def select_output_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self.output_edit.setText(d)

    def get_command(self):
        """
        Construct the command to run ImageJ macro with input and output paths
        Current_dir is subject to error depending on how the script is run.
        """
        # current_dir = Path(__file__).parent.resolve()
        # script_path = current_dir / "macro_moj.py"

        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = "{0}{1}ImageJ{1}macros{1}macro_moj.py".format(base_dir,os.sep)

        if platform == "win32":
            """
            I don't like hard coding the file name here, especially since it is no longer the correct name for Fiji.
            """
            # fiji_path = current_dir.parent / "ImageJ-win64.exe"
            fiji_path = "{0}{1}ImageJ{1}ImageJ-win64.exe".format(base_dir,os.sep)

        else:
            fiji_path = Path("/Users/pguerra/Library/CloudStorage/OneDrive-UniversityofNorthCarolinaatChapelHill/Desktop/Fiji")

        # if not fiji_path.exists():
        if not os.path.isfile(fiji_path):
            self.log_to_console(f"ERROR: Fiji not found at {fiji_path}", "red")
            return None

        return str(fiji_path), ["--console", "-macro", str(script_path)]

    def log_to_console(self, text, color="#a9b7c6"):
        self.console.moveCursor(QTextCursor.End)
        # always precede printed line with datetime stamp
        self.console.insertHtml(f"<span style='color: {color};'>[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}</span><br>")
        self.console.ensureCursorVisible()

    def get_input_path(self):
        input_path = self.input_edit.text().strip()

        if not input_path:
            self.log_to_console("ERROR: Input image path is required.", "red")
            return None

        if not os.path.exists(input_path):
            self.log_to_console(f"ERROR: Input path does not exist: {input_path}", "red")
            return None

        return input_path
    
    def get_output_path(self, input_path):
        text = self.output_edit.text().strip()
        if text:
            base = Path(text)
        else:
            base = Path(input_path)
            self.output_edit.setText(str(input_path))

        output_path = Path(base / "countPHICS_output").resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        return output_path

    def write_config(self, input_path, output_path):
        config_path = output_path / "countPHICS_params.txt"

        lines = [
            "input=" + str(input_path),
            "output=" + str(output_path),

            # "auto_threshold=" + str(self.chk_auto_thresh.isChecked()).lower(),
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
                "roi_thickness=" + str(self.spin_roi_thickness.value())
            ])

        image_files = [
            str(file)
            for file in Path(input_path).glob("*")
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

        key_keywords = [
            "warning",
            "Warning"
        ]
        for line in data.splitlines():
            # Only log the line if NONE of the junk keywords are in it
            if any(key in line for key in key_keywords):
                self.log_to_console(line.strip(), "#d8a63b")
                
        # for line in data.splitlines():
        #     # Only log the line if NONE of the junk keywords are in it
        #     if not any(key in line for key in junk_keywords):
        #         self.log_to_console(line.strip(), "#eeec62")

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

    # ctypes allows the icon to be displayed correctly
    import ctypes
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("countphics.app.1")

    base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / "assets" / "countphics.ico"
    
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(icon_path)))
    
    window = FijiRunnerGUI()
    window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    sys.exit(app.exec())