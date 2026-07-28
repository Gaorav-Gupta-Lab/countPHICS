"""
Dynamic dialog for assigning treatment and replicate values.
Shows only one empty row at a time and adds a new row when the
current last row becomes complete.
"""

from PySide6.QtWidgets import (
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QSpinBox, QLineEdit, QLabel,
    QGridLayout, QDialog, QScrollArea, QFrame
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
        self.setWindowTitle("Assign Groups")
        self.setObjectName("group_assignment_dialog")
        self.image_paths = image_paths
        self.cell_line = cell_line.strip() if cell_line else "UnknownCellLine"
        self.treatment_name = treatment_name.strip() if treatment_name else "UnknownTreatment"
        self.setStyleSheet(load_stylesheet())

        self.rows = []
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        title = QLabel("Assign groups")
        title.setObjectName("group_dialog_title")
        outer.addWidget(title)

        instruction = QLabel("Define each treatment value and the number of matching image replicates.")
        instruction.setObjectName("group_dialog_instruction")
        instruction.setWordWrap(True)
        outer.addWidget(instruction)

        context_card = QFrame()
        context_card.setObjectName("group_dialog_context")
        context_layout = QGridLayout(context_card)
        context_layout.setContentsMargins(14, 12, 14, 12)
        context_layout.setHorizontalSpacing(18)
        context_layout.setVerticalSpacing(6)

        cell_line_label = QLabel("Cell line")
        cell_line_label.setObjectName("group_dialog_context_label")
        cell_line_value = QLabel(self.cell_line)
        cell_line_value.setObjectName("group_dialog_context_value")
        treatment_label = QLabel("Treatment name")
        treatment_label.setObjectName("group_dialog_context_label")
        treatment_value = QLabel(self.treatment_name)
        treatment_value.setObjectName("group_dialog_context_value")

        context_layout.addWidget(cell_line_label, 0, 0)
        context_layout.addWidget(cell_line_value, 0, 1)
        context_layout.addWidget(treatment_label, 1, 0)
        context_layout.addWidget(treatment_value, 1, 1)
        context_layout.setColumnStretch(1, 1)
        outer.addWidget(context_card)

        assignments_card = QFrame()
        assignments_card.setObjectName("group_dialog_assignments")
        assignments_layout = QVBoxLayout(assignments_card)
        assignments_layout.setContentsMargins(14, 14, 14, 14)
        assignments_layout.setSpacing(10)

        assignments_title = QLabel("Group definitions")
        assignments_title.setObjectName("group_dialog_section_title")
        assignments_layout.addWidget(assignments_title)

        scroll = QScrollArea()
        scroll.setObjectName("group_dialog_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        assignments_layout.addWidget(scroll, 1)
        outer.addWidget(assignments_card, 1)

        content = QWidget()
        content.setObjectName("group_dialog_content")
        self.grid = QGridLayout(content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(6)

        self.grid.setColumnStretch(0, 3)
        self.grid.setColumnStretch(1, 2)
        self.grid.setRowMinimumHeight(0, 38)

        header_treatment = QLabel("Treatment")
        header_treatment.setObjectName("group_dialog_column_header")
        header_treatment.setFixedHeight(38)
        header_replicates = QLabel("Replicates")
        header_replicates.setObjectName("group_dialog_column_header")
        header_replicates.setFixedHeight(38)

        self.grid.addWidget(header_treatment, 0, 0)
        self.grid.addWidget(header_replicates, 0, 1)

        scroll.setWidget(content)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch(1)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("group_dialog_continue")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("group_dialog_cancel")

        self.continue_btn.clicked.connect(self._validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(self.continue_btn)
        btn_row.addWidget(self.cancel_btn)
        outer.addLayout(btn_row)

        self._append_empty_row()
        self.resize(560, 600)

    def _append_empty_row(self):
        idx = len(self.rows)

        treatment_edit = QLineEdit()
        treatment_edit.setObjectName("group_dialog_input")
        treatment_edit.setPlaceholderText("e.g. 2.5")
        treatment_edit.setValidator(QDoubleValidator(bottom=-1e12, top=1e12, decimals=6))
        treatment_edit.textChanged.connect(self._on_row_changed)

        replicates_spin = QSpinBox()
        replicates_spin.setObjectName("group_dialog_input")
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
