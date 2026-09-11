# Copyright 2026 Trieflow LLC. GPL-3.0; see LICENSE.
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from core.quarantine import load_receipt, payload_path


class QuarantineDialog(QDialog):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.receipt = None
        self.setWindowTitle("Quarantine Receipts — TwinQuay")
        self.resize(1100, 530)
        layout = QVBoxLayout(self)
        self.caption = QLabel(
            "Open a receipt.json from a quarantine folder. Restore checks payload bytes and never overwrites an occupied original path."
        )
        self.caption.setTextFormat(Qt.TextFormat.PlainText)
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        open_button = QPushButton("Open receipt…")
        open_button.clicked.connect(self.open_receipt)
        layout.addWidget(open_button)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Restore", "Original path", "Quarantined payload", "Status", "Detail"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.restore = buttons.addButton("Restore selected", QDialogButtonBox.ButtonRole.AcceptRole)
        self.restore.clicked.connect(self.restore_selected)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.restore.setEnabled(False)
        receipt = app.model.last_cleanup_receipt
        if receipt is not None:
            self.read_receipt(receipt.receipt_path)

    def open_receipt(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open quarantine receipt", "", "Quarantine receipt (*.json)")
        if filename:
            self.read_receipt(Path(filename))

    def read_receipt(self, filename):
        try:
            self.receipt = load_receipt(filename)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Cannot read receipt", str(exc))
            return
        self.caption.setText(
            f"{filename}\nSelect items to restore. Existing original files are always kept. A failed or interrupted item may require manual review of its payload folder."
        )
        self.table.setRowCount(len(self.receipt.items))
        for row, item in enumerate(self.receipt.items):
            select = QTableWidgetItem()
            eligible = bool(item.sha256 and item.status != "restored")
            select.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled if eligible else Qt.ItemFlag.NoItemFlags
            )
            select.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, select)
            for col, text in enumerate(
                [item.original_path, str(payload_path(self.receipt, item)), item.status, item.detail], 1
            ):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                self.table.setItem(row, col, cell)
        self.restore.setEnabled(True)

    def restore_selected(self):
        selected = [
            item.item_id
            for row, item in enumerate(self.receipt.items)
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        ]
        if self.app.model.restore_quarantine(self.receipt.receipt_path, selected):
            self.accept()
