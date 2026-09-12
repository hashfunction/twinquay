"""Headless Qt state tests, not a substitute for Windows keyboard/DPI acceptance."""

import os
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from core.cleanup_plan import CleanupCandidate, CleanupPlan, EvidenceKind
from qt.cleanup_plan_dialog import CleanupPlanDialog
from qt.quarantine_dialog import QuarantineDialog
from core.quarantine import execute_plan


@pytest.fixture(scope="module")
def application():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication([])
    yield app


def make_plan(tmp_path, evidence=EvidenceKind.EXACT_CONTENT):
    left, right = tmp_path / "duplicate.txt", tmp_path / "reference.txt"
    left.write_bytes(b"same")
    right.write_bytes(b"same")
    return CleanupPlan.create([CleanupCandidate.capture(left, right, evidence)])


def test_preview_requires_destination_and_respects_selection(application, tmp_path):
    plan = make_plan(tmp_path)
    dialog = CleanupPlanDialog(None, SimpleNamespace(model=None), plan)
    assert not dialog.execute.isEnabled()
    assert plan.candidates[0].path.exists()
    dialog.folder.setText(str(tmp_path / "quarantine"))
    dialog.update_summary()
    assert dialog.execute.isEnabled()
    dialog.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    assert not dialog.execute.isEnabled()
    assert not dialog.selected_plan().candidates
    dialog.close()


def test_disabled_similarity_cannot_be_forced_into_selection(application, tmp_path):
    dialog = CleanupPlanDialog(None, SimpleNamespace(model=None), make_plan(tmp_path, EvidenceKind.SIMILARITY))
    assert not dialog.table.item(0, 0).flags() & Qt.ItemFlag.ItemIsEnabled
    dialog.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    dialog.folder.setText(str(tmp_path / "quarantine"))
    dialog.update_summary()
    assert not dialog.execute.isEnabled()
    assert not dialog.selected_plan().candidates
    dialog.close()


def test_receipt_preview_does_not_restore_until_selected(application, tmp_path):
    plan = make_plan(tmp_path)
    receipt = execute_plan(plan, tmp_path / "quarantine")
    dialog = QuarantineDialog(None, SimpleNamespace(model=SimpleNamespace(last_cleanup_receipt=receipt)))
    assert dialog.table.item(0, 0).checkState() == Qt.CheckState.Unchecked
    assert dialog.table.item(0, 1).text() == str(plan.candidates[0].path)
    assert not plan.candidates[0].path.exists()
    dialog.close()


def test_packaged_resources_use_pyinstaller_root(tmp_path, monkeypatch):
    import importlib
    import sys
    from qt import platform

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    importlib.reload(platform)
    try:
        assert platform.BASE_PATH == str(tmp_path)
    finally:
        monkeypatch.delattr(sys, "_MEIPASS")
        importlib.reload(platform)


def test_explicit_legacy_import_copies_scan_preferences_only(application, tmp_path):
    from PyQt6.QtCore import QSettings
    from qt.preferences import Preferences

    old_path = tmp_path / "old.ini"
    old = QSettings(str(old_path), QSettings.Format.IniFormat)
    old.setValue("FilterHardness", 80)
    old.setValue("CustomCommand", "never import commands")
    old.setValue("Portable", True)
    old.sync()
    preferences = Preferences()
    preferences._settings = QSettings(str(tmp_path / "DupliSift.ini"), QSettings.Format.IniFormat)
    preferences.load()
    assert preferences.import_scan_preferences(old_path) == 1
    assert preferences.filter_hardness == 80
    assert preferences.custom_command == ""
    assert preferences.portable is False
    assert old.value("FilterHardness", type=int) == 80


def test_receipts_are_available_from_fresh_startup(application, tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from hscommon import desktop
    from qt import preferences
    from qt.app import DupeGuru

    monkeypatch.setattr(desktop, "special_folder_path", lambda *args, **kwargs: str(tmp_path / "data"))
    monkeypatch.setattr(
        preferences, "create_qsettings", lambda: QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    controller = DupeGuru()
    try:
        assert controller.actionQuarantineReceipts in controller.directories_dialog.menuFile.actions()
        assert controller.actionImportLegacySettings in controller.directories_dialog.menuFile.actions()
    finally:
        for widget in application.topLevelWidgets():
            widget.close()
