"""
Dynamic dialog for assigning treatment and replicate values.
Shows only one empty row at a time and adds a new row when the
current last row becomes complete.
"""

from PySide6.QtWidgets import (
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QSpinBox, QLineEdit, QLabel,
    QGridLayout, QDialog, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from libraries.StyleSheetLoader import load_stylesheet


class GroupAssignmentDialog(QDialog):
    """
    Dynamic dialog for assigning treatment and replicate values.
    Shows only one empty row at a time and adds a new row when the
    current last row becomes complete.
    """

    def __init__(self, image_paths: list[str], cell_line: str, treatment_name: str, parent=None):
        super().__init__(parent)
        # self.setWindowTitle("Manual Group Assignment")
        self.image_paths = image_paths
        self.cell_line = cell_line.strip() if cell_line else "UnknownCellLine"
        self.treatment_name = treatment_name.strip() if treatment_name else "UnknownTreatment"
        self.setStyleSheet(load_stylesheet())

        self.rows = []
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(2)

        header = QLabel(
            f"<div style='line-height:1.15;'>"
            f"<span style='font-size:15px; font-weight:700; color: #302424;'>Cell line:</span> {self.cell_line}<br>"
            f"<span style='font-size:15px; font-weight:700; color: #302424;'>Treatment name:</span> {self.treatment_name}<br>"
            f"<span style='font-size:13px; color: #302424;'>Enter treatment values and replicate counts below.</span>"
            f"</div>"
        )

        header.setObjectName("header_label")
        header.setWordWrap(True)
        outer.addWidget(header, 0, alignment=Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll, 1)

        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(6)

        self.grid.setColumnStretch(0, 3)
        self.grid.setColumnStretch(1, 2)

        header_treatment = QLabel("Treatment")
        header_treatment.setObjectName("header_label")
        header_replicates = QLabel("Replicates")
        header_replicates.setObjectName("header_label")

        self.grid.addWidget(header_treatment, 0, 0)
        self.grid.addWidget(header_replicates, 0, 1)

        scroll.setWidget(content)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
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

        self._append_empty_row()
        self.resize(500, 540)

    def _append_empty_row(self):
        idx = len(self.rows)

        treatment_edit = QLineEdit()
        treatment_edit.setPlaceholderText("e.g. 2.5")
        treatment_edit.setValidator(QDoubleValidator(bottom=-1e12, top=1e12, decimals=6))
        treatment_edit.textChanged.connect(self._on_row_changed)

        replicates_spin = QSpinBox()
        replicates_spin.setRange(0, 9999)
        replicates_spin.setSpecialValueText("")
        replicates_spin.valueChanged.connect(self._on_row_changed)

        self.grid.addWidget(treatment_edit, idx + 1, 0)
        self.grid.addWidget(replicates_spin, idx + 1, 1)

        self.rows.append({
            "treatment": treatment_edit,
            "replicates": replicates_spin,
        })

    def _row_is_complete(self, idx: int) -> bool:
        row = self.rows[idx]

        treatment_ok = row["treatment"].text().strip() != ""
        replicates_ok = row["replicates"].value() > 0
        return treatment_ok and replicates_ok

    def _on_row_changed(self):
        # Ensure exactly one empty row at the bottom
        if self._row_is_complete(len(self.rows) - 1):
            self._append_empty_row()

    def _validate_and_accept(self):
        assignments = self.get_assignment_list()
        if not assignments:
            return
        self.accept()

    # def get_assignment_list(self) -> list[dict]:
    def get_assignment_list(self) -> str:
        # out1 = []
        # Much simpler to build groupings as a string that is eventually converted to a list.
        out = ""
        for i, row in enumerate(self.rows):
            if not self._row_is_complete(i):
                break

            for _ in range(row["replicates"].value()):
                out += row["treatment"].text() + ","

            """
            out1.append({
                "treatment": float(row["treatment"].text()),
                "replicates": int(row["replicates"].value()),
            })
            """
        out = out[:-1]
        return out
