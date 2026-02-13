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

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QHBoxLayout,
    QFileDialog, QCheckBox, QSpinBox, QGroupBox, QDoubleSpinBox, QLineEdit, QLabel,
    QGridLayout, QDialog, QMessageBox, QScrollArea, QSizePolicy
)

from PySide6.QtCore import QProcess, Qt, QSignalBlocker
from PySide6.QtGui import QTextCursor, QIcon
from typer import edit

from ImageJ.macros.grapher import FIJIGrapher
from PySide6.QtWidgets import QComboBox

class GroupAssignmentDialog(QDialog):
    """
    Modal dialog allowing the user to assign a group name per image.
    Includes "same as above" behavior that copies/locks the group field.
    """

    def __init__(self, image_paths: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Group Assignment")
        self.image_paths = image_paths
        self.setStyleSheet(FijiRunnerGUI.load_stylesheet())

        self.group_edits: list[QLineEdit] = []
        self.same_as_above_checks: list[QCheckBox] = []

        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QLabel("Assign a sample group for each image:")
        header.setStyleSheet("font-weight: 600;")
        outer.addWidget(header)

        # Scroll area so large image sets don't explode the window
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, 1)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("<b>Image</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Group</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Same as above</b>"), 0, 2, alignment=Qt.AlignCenter)

        for i, p in enumerate(self.image_paths, start=1):
            img_label = QLabel(Path(p).name)
            img_label.setToolTip(p)
            img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            group_edit = QLineEdit()
            group_edit.setPlaceholderText("e.g., WT, KO, +Drug, etc.")
            same_chk = QCheckBox()

            self.group_edits.append(group_edit)
            self.same_as_above_checks.append(same_chk)

            # First row can't be "same as above"
            if i == 1:
                same_chk.setEnabled(False)

            same_chk.toggled.connect(lambda checked, idx=i - 1: self._on_same_as_above_toggled(idx, checked))

            grid.addWidget(img_label, i, 0)
            grid.addWidget(group_edit, i, 1)
            grid.addWidget(same_chk, i, 2, alignment=Qt.AlignCenter)

        scroll.setWidget(content)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("browse_btn")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("browse_btn")
        self.continue_btn.clicked.connect(self._validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(self.continue_btn)
        btn_row.addWidget(self.cancel_btn)
        outer.addLayout(btn_row)

        self.resize(900, 600)

    def _on_group_text_changed(self, idx: int):
        """
        Whenever a group text changes, update any downstream rows that are
        currently "same as above" linked (directly or via a chain).
        """
        self._propagate_from(idx)

    def _propagate_from(self, start_idx: int):
        """
        Push the effective group value from start_idx to subsequent rows
        that are checked "same as above", until the chain breaks.
        """
        # Determine the source value to propagate (effective text at start_idx)
        src_text = self.group_edits[start_idx].text()

        # Walk downward, updating linked rows
        for j in range(start_idx + 1, len(self.group_edits)):
            if not self.same_as_above_checks[j].isChecked():
                break  # chain stops at first unchecked row

            edit = self.group_edits[j]

            # Avoid recursive signal loops + unnecessary work
            if edit.text() != src_text:
                with QSignalBlocker(edit):
                    edit.setText(src_text)

    def _on_same_as_above_toggled(self, idx: int, checked: bool):
        """
        If checked: copy group from previous row, disable + visually gray out.
        If unchecked: enable editing again.
        """
        edit = self.group_edits[idx]

        if checked:
            # lock it
            edit.setEnabled(False)
            edit.setProperty("same_as_above_locked", True)

            # set to the effective value of the row above (and propagate further)
            above_text = self.group_edits[idx - 1].text()
            with QSignalBlocker(edit):
                edit.setText(above_text)
            self._propagate_from(idx - 1)

        else:
            edit.setEnabled(True)
            edit.setProperty("same_as_above_locked", False)
            # optional: clear when unlocking
            # edit.clear()

        edit.style().unpolish(edit)
        edit.style().polish(edit)
        edit.update()

    def _validate_and_accept(self):
        """
        Validate:
        - each effective group must be non-empty
        - "same as above" rows require the above row to have a group
        """
        # Force-update "same as above" rows in case user edited the above row after checking
        for i in range(1, len(self.image_paths)):
            if self.same_as_above_checks[i].isChecked():
                self.group_edits[i].setText(self.group_edits[i - 1].text().strip())

        missing = []
        for i, p in enumerate(self.image_paths):
            g = self.group_edits[i].text().strip()
            if not g:
                missing.append(Path(p).name)

        if missing:
            QMessageBox.warning(
                self,
                "Missing group names",
                "Every image needs a group name.\n\nMissing:\n- " + "\n- ".join(missing[:20]) +
                ("\n\n(…and more)" if len(missing) > 20 else "")
            )
            return

        self.accept()

    def get_group_map(self) -> dict[str, str]:
        """
        Returns: {image_path: group_name, ...}
        """
        # Ensure "same as above" is propagated
        for i in range(1, len(self.image_paths)):
            if self.same_as_above_checks[i].isChecked():
                self.group_edits[i].setText(self.group_edits[i - 1].text().strip())

        out: dict[str, str] = {}
        for p, edit in zip(self.image_paths, self.group_edits):
            g = edit.text().strip()
            out[p] = g
        return out


class FijiRunnerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Colony Counter Interface")

        screen = self.screen()
        screen_geometry = screen.geometry()
        width = int(screen_geometry.width() * 0.7)
        height = int(screen_geometry.height() * 0.7)
        self.resize(width, height)

        # self.resize(1000, 700)

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
        self.group_assignment_label = QLabel("Group assignment:")
        self.combo_group_assignment = QComboBox()
        self.combo_group_assignment.addItems(["None", "Automatic", "Manual"])

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
        self.input_edit.setPlaceholderText("Select Folder Containing Images")
        self.input_btn.setObjectName("browse_btn")
        self.input_btn.clicked.connect(self.select_input_folder)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Input folder:"))
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
        
        # ---- GENERAL SETTINGS ----
        general_box = QGroupBox("General settings")
        general_layout = QVBoxLayout()

        general_layout.addWidget(self.chk_same_roi)
        general_layout.addWidget(self.chk_six_well)
        general_layout.addWidget(self.chk_plotting)

        self.group_assignment_label.setObjectName("group_assignment_label")
        general_layout.addWidget(self.group_assignment_label)
        general_layout.addWidget(self.combo_group_assignment)

        general_box.setLayout(general_layout)
        settings_container.addWidget(general_box, 1)

        # ---- ADVANCED SETTINGS ----
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

        advanced_layout.addWidget(label_rolling_radius, 0, 0); advanced_layout.addWidget(self.spin_rolling, 0, 1)
        advanced_layout.addWidget(label_min_col_size, 0, 2); advanced_layout.addWidget(self.spin_min_col, 0, 3)
        advanced_layout.addWidget(label_max_col_size, 1, 2); advanced_layout.addWidget(self.spin_max_col, 1, 3)
        advanced_layout.addWidget(label_circularity, 1, 0); advanced_layout.addWidget(self.spin_circ, 1, 1)
        advanced_layout.addWidget(label_sigma, 0, 4); advanced_layout.addWidget(self.spin_sigma, 0, 5)
        advanced_layout.addWidget(label_roi_thickness, 1, 4); advanced_layout.addWidget(self.spin_roi_thickness, 1, 5)

        advanced_box.setLayout(advanced_layout)
        settings_container.addWidget(advanced_box, 3)
        
        # Add the horizontal settings container to the main layout
        layout.addLayout(settings_container)

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
        if not self.output_edit.text().strip():
            self.output_edit.setText(file_input_folder)

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

    def list_image_files(self, input_path: str) -> list[str]:
        image_files = [
            str(file)
            for file in Path(input_path).glob("*")
            if file.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]
        ]
        return natsort.natsorted(image_files)


    def write_config(self, input_path, output_path, group_map: dict[str, list[str]] | None = None):
        # config_path = output_path / "countPHICS_params.txt"
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(base_path, "config_dir")
        os.makedirs(config_dir, exist_ok=True)
        config_path = f"{config_dir}{os.sep}countPHICS_params.txt"

        lines = [
            "input=" + str(input_path),
            "output=" + str(output_path),

            "same_roi=" + str(self.chk_same_roi.isChecked()).lower(),
            "six_well=" + str(self.chk_six_well.isChecked()).lower(),
            "group_assignment=" + str(self.combo_group_assignment.currentText()).lower(),

            "rolling_ball=" + str(self.spin_rolling.value()),
            "min_colony=" + str(self.spin_min_col.value()),
            "max_colony=" + str(self.spin_max_col.value()),
            "circularity=" + str(self.spin_circ.value()),
            "sigma=" + str(self.spin_sigma.value()),
            "roi_thickness=" + str(self.spin_roi_thickness.value()),
        ]

        image_files = self.list_image_files(input_path)
        lines.append("images=" + ";".join(image_files))

        # Write groups as a dictionary: group_name -> [image_path, ...]
        # Stored as JSON so it's unambiguous to parse later.
        if group_map is not None:
            # lines.append("groups=" + json.dumps(group_map))
            entries = []
            for img_path, group in group_map.items():
                entries.append(f"{img_path}|||{group}")
            lines.append("groups=" + ";;".join(entries))

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

        image_files = self.list_image_files(input_path)
        if not image_files:
            self.log_to_console("ERROR: No image files found in input folder.", "red")
            return

        group_map = None
        if self.combo_group_assignment.currentText() == "Manual":
            dlg = GroupAssignmentDialog(image_files, parent=self)
            if dlg.exec() != QDialog.Accepted:
                self.log_to_console("Launch canceled during group assignment.", "#d8a63b")
                return
            group_map = dlg.get_group_map()

        output_path = self.get_output_path(input_path)
        self.write_config(input_path, output_path, group_map=group_map)
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
        ]
        for line in data.splitlines():
            # Only log the line if NONE of the junk keywords are in it
            if any(key in line.lower() for key in key_keywords):
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
            if self.chk_plotting.isChecked():
                grapher = FIJIGrapher()

                plots_dir = output_dir / "plots"
                plots_dir.mkdir(exist_ok=True)

                # Generate boxplot for colony counts
                grapher.load_summary_file(summary_file)
                grapher.boxplot(
                    x="Group",
                    y="Num colonies",
                    title="Mean colony count by group"
                )
                grapher.save_current_plot(plots_dir / "all_colony_counts_boxplot.png")
                plt.close()

                grapher.violin(
                    x="Group",
                    y="GeomMeanSize",
                    title="Mean size by group (geometric mean of colony areas)"
                )
                grapher.save_current_plot(plots_dir / "all_colony_counts_violinplot.png")
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
            else:
                self.log_to_console(
                    "Plotting skipped (unchecked in settings)", "#97af2a"
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