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
from PyQt6.QtCore import QPoint, QRect, QSettings, Qt
from PyQt6.QtGui import QKeySequence, QShowEvent
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


def test_default_contents_scan_finds_the_original_sample_pair(controller, tmp_path, monkeypatch):
    from core.scanner import ScanType
    from hscommon.jobprogress import job

    root = tmp_path / "Cedar House Review"
    root.mkdir()
    fixture = prepare(root)
    controller.directories_dialog.scanTypeComboBox.setCurrentIndex(1)
    controller._update_options()
    assert controller.model.options["scan_type"] == ScanType.CONTENTS
    assert controller.model.options["size_threshold"] == 10 * 1024
    controller.model.add_directory(fixture["input"])
    # Only scheduling is synchronous; production options, enumeration and content
    # matching run unchanged against the exact native workflow fixture.
    monkeypatch.setattr(controller.model, "_start_job", lambda job_id, work: work(job.nulljob))
    controller.model.start_scanning()
    scan_type, groups, discarded = controller.model._pending_scan_result
    assert scan_type == ScanType.CONTENTS and discarded == 0
    assert len(groups) == 1
    assert {item.path for item in groups[0]} == {
        root / "Project Documents/Cedar House Brief.txt",
        root / "Project Documents/Cedar House Brief - emailed.txt",
    }


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


def test_recent_folder_menu_arrows_enter_open_actual_add_folder_action(controller, monkeypatch):
    from PyQt6.QtTest import QTest

    directory = controller.directories_dialog
    observed = []
    monkeypatch.setattr(QFileDialog, "exec", lambda dialog: observed.append(dialog.windowTitle()) or 0)
    assert directory.recentFolders.isEmpty()
    assert directory.addFolderButton.menu() is None
    directory.addFolderButton.click()
    assert observed == ["Select a folder to add to the scanning list"]
    previous = "D:/a/_temp/.duplisift-install-previous/Cedar House Review/Project Documents"
    directory.recentFolders.insertItem(previous)
    menu = directory.addFolderButton.menu()
    assert menu is directory.menuRecentFolders
    assert menu.actions()[0] is directory.actionAddFolder
    assert menu.actions()[0].text() == "Add Folder..." and menu.actions()[0].isEnabled()
    assert menu.actions()[-1].text() == "Clear List"
    history = list(directory.recentFolders._items)
    starts = [None] + [action for action in menu.actions() if not action.isSeparator()]
    for initial in starts:
        menu.popup(QPoint(30, 30))
        menu.setActiveAction(initial)
        for _ in range(12):
            if menu.activeAction() is directory.actionAddFolder:
                break
            key = Qt.Key.Key_Up if menu.activeAction() else Qt.Key.Key_Down
            QTest.keyClick(menu, key)
        assert menu.activeAction() is directory.actionAddFolder
        QTest.keyClick(menu, Qt.Key.Key_Return)
    assert observed == ["Select a folder to add to the scanning list"] * (1 + len(starts))
    assert directory.recentFolders._items == history
    assert "Wait-TwinQuayWorkflowAddFolderChooser" in SCRIPT


def test_real_plan_widget_saves_exact_reviewed_selection(controller, tmp_path, monkeypatch):
    from qt.cleanup_plan_dialog import CleanupPlanDialog

    root = tmp_path / "fixture"
    root.mkdir()
    prepare(root)
    plan = CleanupPlan.create(
        [
            CleanupCandidate.capture(
                root / "Project Documents/Cedar House Brief - emailed.txt", root / "Project Documents/Cedar House Brief.txt", EvidenceKind.EXACT_CONTENT
            )
        ]
    )
    dialog = CleanupPlanDialog(controller.resultWindow, controller, plan)
    assert dialog.windowTitle() in SCRIPT
    assert dialog.table.rowCount() == 1 and dialog.table.columnCount() == 7
    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Checked
    assert dialog.table.item(0, 1).text() == str(root / "Project Documents/Cedar House Brief - emailed.txt")
    assert dialog.table.item(0, 2).text() == str(root / "Project Documents/Cedar House Brief.txt")
    assert dialog.table.item(0, 3).text() == "Contents"
    assert dialog.folder.accessibleName() in SCRIPT
    for button in dialog.findChildren(QPushButton):
        if button.text() in ("Save plan…", "Choose folder…", "Verify and quarantine selected"):
            assert button.text() in SCRIPT
    titles = []

    def filename(parent, title, *args):
        titles.append(title)
        return str(root / "Cedar House - Cleanup Plan.json"), "JSON plan (*.json)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", filename)
    dialog.save_plan()
    assert titles == ["Save selected cleanup plan"] and titles[0] in SCRIPT
    assert verify_plan(root)["candidate_count"] == 1
    assert json.loads((root / "Cedar House - Cleanup Plan.json").read_text()) == json.loads(json.dumps(plan.to_dict()))
    dialog.close()


def test_review_dialog_fits_1024_desktop_with_native_frame(controller, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from qt import util as qt_util
    from qt.cleanup_plan_dialog import CleanupPlanDialog

    class FourPixelFrameReview(CleanupPlanDialog):
        def frameGeometry(self):
            frame = QRect(self.geometry())
            frame.setWidth(frame.width() + 4)
            return frame

    screen = QRect(0, 0, 1024, 768)
    display = SimpleNamespace(availableGeometry=lambda: QRect(screen))
    monkeypatch.setattr(
        qt_util,
        "QGuiApplication",
        SimpleNamespace(screenAt=lambda _point: display, screens=lambda: [display]),
    )
    root = tmp_path / "geometry-fixture"
    root.mkdir()
    prepare(root)
    plan = CleanupPlan.create(
        [
            CleanupCandidate.capture(
                root / "Project Documents/Cedar House Brief - emailed.txt",
                root / "Project Documents/Cedar House Brief.txt",
                EvidenceKind.EXACT_CONTENT,
            )
        ]
    )
    dialog = FourPixelFrameReview(controller.resultWindow, controller, plan)
    dialog.resize(1024, 590)
    dialog.move(0, 56)
    assert dialog.frameGeometry().width() == 1028

    dialog.showEvent(QShowEvent())
    dialog.layout().activate()

    assert dialog.width() == 1020
    assert dialog.frameGeometry().width() == 1024
    assert screen.contains(dialog.frameGeometry())
    assert dialog.table.width() >= 700
    for text in ("Choose folder…", "Save plan…", "Verify and quarantine selected", "Cancel"):
        button = next(button for button in dialog.findChildren(QPushButton) if button.text() == text)
        button_rect = QRect(button.mapTo(dialog, QPoint(0, 0)), button.size())
        assert button.width() > 0 and button.height() > 0
        assert dialog.rect().contains(button_rect), text
    dialog.close()


def test_actual_receipt_table_checkbox_and_restore_command(controller, tmp_path, monkeypatch):
    from qt.quarantine_dialog import QuarantineDialog

    root = tmp_path / "fixture"
    root.mkdir()
    prepare(root)
    plan = CleanupPlan.create(
        [
            CleanupCandidate.capture(
                root / "Project Documents/Cedar House Brief - emailed.txt", root / "Project Documents/Cedar House Brief.txt", EvidenceKind.EXACT_CONTENT
            )
        ]
    )
    receipt = execute_plan(plan, root / "Review Copies")
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


def test_receipt_dialog_fits_1024_desktop_with_native_frame(controller, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from qt import util as qt_util
    from qt.quarantine_dialog import QuarantineDialog

    class FourPixelFrameReceipt(QuarantineDialog):
        def frameGeometry(self):
            frame = QRect(self.geometry())
            frame.setWidth(frame.width() + 4)
            return frame

    screen = QRect(0, 0, 1024, 768)
    display = SimpleNamespace(availableGeometry=lambda: QRect(screen))
    monkeypatch.setattr(
        qt_util,
        "QGuiApplication",
        SimpleNamespace(screenAt=lambda _point: display, screens=lambda: [display]),
    )
    root = tmp_path / "receipt-geometry-fixture"
    root.mkdir()
    prepare(root)
    plan = CleanupPlan.create(
        [
            CleanupCandidate.capture(
                root / "Project Documents/Cedar House Brief - emailed.txt",
                root / "Project Documents/Cedar House Brief.txt",
                EvidenceKind.EXACT_CONTENT,
            )
        ]
    )
    controller.model.last_cleanup_receipt = execute_plan(plan, root / "Review Copies")
    dialog = FourPixelFrameReceipt(controller.resultWindow, controller)
    dialog.resize(1024, 530)
    dialog.move(0, 86)
    assert dialog.frameGeometry() == QRect(0, 86, 1028, 530)

    dialog.showEvent(QShowEvent())
    dialog.layout().activate()

    assert dialog.width() == 1020
    assert dialog.frameGeometry().width() == 1024
    assert screen.contains(dialog.frameGeometry())
    assert dialog.table.width() >= 700
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 3).text() == "quarantined"
    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Unchecked
    for text in ("Open receipt…", "Restore selected", "Close"):
        button = next(button for button in dialog.findChildren(QPushButton) if button.text() == text)
        button_rect = QRect(button.mapTo(dialog, QPoint(0, 0)), button.size())
        assert button.width() > 0 and button.height() > 0
        assert dialog.rect().contains(button_rect), text
    assert dialog.restore.isEnabled()
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
