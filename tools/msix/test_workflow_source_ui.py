# Copyright 2026 Trieflow LLC. MIT.
"""Actual source widget/shortcut contract, offscreen; not Windows UI acceptance."""
import json
import os
from pathlib import Path
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(Path(__file__).parent))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QFileDialog, QPushButton
from core.cleanup_plan import CleanupCandidate, CleanupPlan, EvidenceKind
from core.quarantine import execute_plan
from workflow_files import prepare, verify_plan

SCRIPT = (Path(__file__).parent / "qualify-workflow.ps1").read_text(encoding="utf-8")


@pytest.fixture
def controller(tmp_path, monkeypatch):
    from hscommon import desktop
    from qt import preferences
    from qt.app import DupeGuru

    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(desktop, "special_folder_path", lambda *args, **kwargs: str(tmp_path / "data"))
    monkeypatch.setattr(
        preferences, "create_qsettings", lambda: QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    app = DupeGuru()
    app.model._recreate_result_table()
    yield app
    app.model.results.is_modified = False
    for widget in application.topLevelWidgets():
        widget.close()


def test_actual_scanner_labels_and_result_action_shortcuts(controller):
    directory = controller.directories_dialog
    combo = directory.scanTypeComboBox
    assert [combo.itemText(i) for i in range(combo.count())] == ["Filename", "Contents", "Folders"]
    from PyQt6.QtTest import QTest

    combo.setCurrentIndex(2)
    QTest.keyClick(combo, Qt.Key.Key_Home)
    QTest.keyClick(combo, Qt.Key.Key_Down)
    assert combo.currentText() == "Contents"
    assert directory.scanButton.text() == "Scan"
    assert "'{HOME}{DOWN}'" in SCRIPT
    assert "'Contents'" in SCRIPT and "'Scan'" in SCRIPT
    assert "$combo.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern).Current.Value" in SCRIPT
    for action, shortcut, keys in (
        (controller.resultWindow.actionMakeSelectedReference, "Ctrl+Space", "^ "),
        (controller.resultWindow.actionMarkAll, "Ctrl+A", "^a"),
        (controller.resultWindow.actionDeleteMarked, "Ctrl+D", "^d"),
        (controller.actionQuarantineReceipts, "Ctrl+Shift+Q", "^+q"),
    ):
        assert action.shortcut().toString(QKeySequence.SequenceFormat.PortableText) == shortcut
        assert f"'{keys}'" in SCRIPT


def test_real_plan_widget_saves_exact_reviewed_selection(controller, tmp_path, monkeypatch):
    from qt.cleanup_plan_dialog import CleanupPlanDialog

    root = tmp_path / "fixture"
    root.mkdir()
    prepare(root)
    plan = CleanupPlan.create(
        [
            CleanupCandidate.capture(
                root / "input/duplicate-copy.bin", root / "input/keep-original.bin", EvidenceKind.EXACT_CONTENT
            )
        ]
    )
    dialog = CleanupPlanDialog(controller.resultWindow, controller, plan)
    assert dialog.windowTitle() in SCRIPT
    assert dialog.table.rowCount() == 1 and dialog.table.columnCount() == 7
    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert dialog.table.item(0, 1).text() == str(root / "input/duplicate-copy.bin")
    assert dialog.table.item(0, 2).text() == str(root / "input/keep-original.bin")
    assert dialog.table.item(0, 3).text() == "Contents"
    assert dialog.folder.accessibleName() in SCRIPT
    for button in dialog.findChildren(QPushButton):
        if button.text() in ("Save plan…", "Choose folder…", "Verify and quarantine selected"):
            assert button.text() in SCRIPT
    titles = []

    def filename(parent, title, *args):
        titles.append(title)
        return str(root / "selected-plan.json"), "JSON plan (*.json)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", filename)
    dialog.save_plan()
    assert titles == ["Save selected cleanup plan"] and titles[0] in SCRIPT
    assert verify_plan(root)["candidate_count"] == 1
    assert json.loads((root / "selected-plan.json").read_text()) == json.loads(json.dumps(plan.to_dict()))
    dialog.close()


def test_actual_receipt_table_checkbox_and_restore_command(controller, tmp_path, monkeypatch):
    from qt.quarantine_dialog import QuarantineDialog

    root = tmp_path / "fixture"
    root.mkdir()
    prepare(root)
    plan = CleanupPlan.create(
        [
            CleanupCandidate.capture(
                root / "input/duplicate-copy.bin", root / "input/keep-original.bin", EvidenceKind.EXACT_CONTENT
            )
        ]
    )
    receipt = execute_plan(plan, root / "quarantine")
    controller.model.last_cleanup_receipt = receipt
    dialog = QuarantineDialog(controller.resultWindow, controller)
    assert dialog.windowTitle() in SCRIPT
    assert dialog.table.rowCount() == 1 and dialog.table.columnCount() == 5
    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Unchecked
    assert dialog.table.item(0, 3).text() == "quarantined"
    assert dialog.restore.text() in SCRIPT
    selected = []
    monkeypatch.setattr(controller.model, "restore_quarantine", lambda path, ids: selected.append((path, ids)))
    from PyQt6.QtTest import QTest

    dialog.table.setFocus()
    QTest.keyClick(dialog.table, Qt.Key.Key_Home, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(dialog.table, Qt.Key.Key_Space)
    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert "'^{HOME} '" in SCRIPT
    assert "$toggle.Toggle()" not in SCRIPT
    dialog.restore_selected()
    assert selected == [(receipt.receipt_path, [receipt.items[0].item_id])]
    dialog.close()


def test_real_close_question_and_job_disclosure_match_ui_observer(controller, monkeypatch, tmp_path):
    from core.app import JobType
    from PyQt6.QtGui import QCloseEvent
    from types import SimpleNamespace

    questions = []
    monkeypatch.setattr(controller, "confirm", lambda title, message: questions.append((title, message)) or False)
    controller.model.results.is_modified = True
    event = QCloseEvent()
    controller.directories_dialog.closeEvent(event)
    assert not event.isAccepted()
    assert len(questions) == 1
    assert all(text in SCRIPT for text in questions[0])
    controller.model.results.is_modified = False
    messages = []
    monkeypatch.setattr(controller, "show_message", messages.append)
    receipt_path = tmp_path / "receipt.json"
    for status in ("quarantined", "restore_collision", "restored"):
        controller.model.last_cleanup_receipt = SimpleNamespace(
            receipt_path=receipt_path, items=[SimpleNamespace(status=status)]
        )
        controller.model._job_completed(JobType.RESTORE)
        # The actual model creates this disclosure; the observer must use all of
        # its lines, including exact receipt path and the instruction to rescan.
        prefix, path_line, suffix = messages[-1].split("\n")
        assert prefix == f"1 {status}" and path_line == f"Receipt: {receipt_path}"
        assert suffix in SCRIPT and '"1 $Status`nReceipt: $($Context.facts.plan.receipt_path)`n' in SCRIPT
