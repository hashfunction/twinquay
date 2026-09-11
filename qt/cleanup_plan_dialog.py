# Copyright 2026 Trieflow LLC. GPL-3.0; see LICENSE.
import json
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from core.gui.cleanup_plan import CleanupPlanReview
from core.quarantine import candidate_item_id


class CleanupPlanDialog(QDialog):
    def __init__(self, parent, app, plan):
        super().__init__(parent)
        self.app = app
        self.review = CleanupPlanReview(plan)
        self.setWindowTitle("Review Cleanup Plan — TwinQuay")
        self.resize(1120, 590)
        layout = QVBoxLayout(self)
        title = QLabel("Review before moving files")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)
        note = QLabel(
            "Only Contents scan candidates can be selected. TwinQuay reads both files again byte-for-byte before moving each duplicate. Keep the reference files and quarantine folder until you finish reviewing."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(len(plan.candidates), 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Include",
                "Duplicate to quarantine",
                "Reference to keep",
                "Evidence",
                "Eligibility",
                "Bytes",
                "Planned destination",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        for row, (candidate, eligibility) in enumerate(zip(plan.candidates, self.review.eligibility)):
            include = QTableWidgetItem()
            include.setFlags(
                Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled
                if eligibility.eligible
                else Qt.NoItemFlags
            )
            include.setCheckState(Qt.Checked if eligibility.eligible else Qt.Unchecked)
            self.table.setItem(row, 0, include)
            values = [
                str(candidate.path),
                str(candidate.reference_path),
                "Contents" if candidate.evidence.value == "exact_content" else "Similarity",
                "Ready for fresh byte check" if eligibility.eligible else eligibility.code.replace("_", " "),
                str(candidate.candidate_size),
                "Choose a quarantine folder",
            ]
            for col, value in enumerate(values, 1):
                item = QTableWidgetItem(value)
                item.setToolTip(value + ("\n" + eligibility.detail if col == 4 else ""))
                self.table.setItem(row, col, item)
        layout.addWidget(self.table)
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("&Quarantine folder:"))
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.folder.setAccessibleName("User-selected quarantine folder")
        folder_row.addWidget(self.folder)
        choose = QPushButton("Choose folder…")
        choose.clicked.connect(self.choose_folder)
        folder_row.addWidget(choose)
        layout.addLayout(folder_row)
        self.destination = QLabel(
            "Choose a folder to see the planned destination. A durable receipt is saved beside the quarantined files."
        )
        self.destination.setWordWrap(True)
        self.destination.setTextFormat(Qt.PlainText)
        layout.addWidget(self.destination)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        export = buttons.addButton("Save plan…", QDialogButtonBox.ActionRole)
        export.clicked.connect(self.save_plan)
        self.execute = buttons.addButton("Verify and quarantine selected", QDialogButtonBox.AcceptRole)
        self.execute.clicked.connect(self.execute_plan)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.table.itemChanged.connect(self.update_summary)
        self.update_summary()

    def selected_plan(self):
        indices = {row for row in range(self.table.rowCount()) if self.table.item(row, 0).checkState() == Qt.Checked}
        return self.review.selected_plan(indices)

    def update_summary(self):
        plan = self.selected_plan()
        self.summary.setText(
            f"{len(plan.candidates)} selected · {sum(c.candidate_size for c in plan.candidates):,} bytes · originals remain recoverable from the receipt"
        )
        self.execute.setEnabled(bool(plan.candidates and self.folder.text()))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose quarantine folder")
        if folder:
            self.folder.setText(folder)
            self.destination.setText(
                str(Path(folder) / self.review.plan.plan_id / "payload")
                + "\nEach file receives a unique item folder. receipt.json records its exact original and payload paths."
            )
            for row, candidate in enumerate(self.review.plan.candidates):
                destination = (
                    Path(folder)
                    / self.review.plan.plan_id
                    / "payload"
                    / candidate_item_id(self.review.plan, candidate)
                    / candidate.path.name
                )
                self.table.item(row, 6).setText(str(destination))
                self.table.item(row, 6).setToolTip(str(destination))
            self.update_summary()

    def save_plan(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save selected cleanup plan", "", "JSON plan (*.json)")
        if filename:
            try:
                # The platform dialog may confirm overwrite, but saving a new plan remains exclusive.
                with open(filename, "x", encoding="utf-8") as stream:
                    json.dump(self.selected_plan().to_dict(), stream, ensure_ascii=True, indent=2)
            except OSError as exc:
                QMessageBox.warning(self, "Plan was not saved", str(exc))

    def execute_plan(self):
        if self.app.model.execute_cleanup_plan(self.selected_plan(), self.folder.text()):
            self.accept()
