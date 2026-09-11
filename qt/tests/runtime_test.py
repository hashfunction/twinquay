"""Headless Qt 6 behavior tests, including the real QImage C-extension bridge."""

import os
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt, QEvent, QPointF, QModelIndex
from PyQt6.QtGui import QColor, QImage, QPixmap, QMouseEvent
from PyQt6.QtWidgets import QApplication, QFileDialog


@pytest.fixture(scope="module")
def application():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    yield QApplication.instance() or QApplication([])


def test_native_qimage_capsule_reads_rgb_and_padded_rows(application, tmp_path):
    from qt.pe import _block_qt
    from qt.pe.photo import File

    # Five RGB pixels require row padding. A wrong stride or pixel format
    # produces different block colors even when the native import succeeds.
    image = QImage(5, 7, QImage.Format.Format_RGB888)
    image.fill(QColor(51, 102, 153))
    assert _block_qt.getblocks(image, 2) == [(51, 102, 153)] * 4
    path = tmp_path / "photo-é.png"
    assert image.save(str(path))
    photo = File(path)
    assert photo._plat_get_dimensions() == (5, 7)
    assert photo._plat_get_blocks(2, 1) == [(51, 102, 153)] * 4
    assert photo._plat_get_blocks(2, 6) == [(51, 102, 153)] * 4


def test_all_original_assets_decode_in_source_and_package(application, tmp_path, monkeypatch):
    import shutil
    from qt import platform, resources

    for alias in resources.ASSETS:
        assert not QPixmap(resources.asset_path(alias)).isNull(), alias
    shutil.copytree(Path(platform.BASE_PATH) / "images/twinquay", tmp_path / "images/twinquay")
    monkeypatch.setattr(platform, "BASE_PATH", str(tmp_path))
    for alias in resources.ASSETS:
        assert not QPixmap(resources.asset_path(alias)).isNull(), alias


@pytest.mark.parametrize("mode", ["standard", "music", "picture"])
def test_scan_review_windows_and_options_construct_in_each_mode(application, tmp_path, monkeypatch, mode):
    from core.app import AppMode
    from hscommon import desktop
    from qt import preferences
    from qt.app import DupeGuru

    monkeypatch.setattr(desktop, "special_folder_path", lambda *args, **kwargs: str(tmp_path / "data"))
    monkeypatch.setattr(
        preferences, "create_qsettings", lambda: QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    controller = DupeGuru()
    try:
        controller.model.app_mode = {"standard": AppMode.STANDARD, "music": AppMode.MUSIC, "picture": AppMode.PICTURE}[
            mode
        ]
        # Saved pre-migration preferences use plain integers for dock areas.
        controller.prefs.set_value("DetailsWindowRect", [0, 1, 8, 0, 0, 400, 300])
        controller.model._recreate_result_table()
        options = controller._get_preferences_dialog_class()(controller.resultWindow, controller)
        options.load()
        assert controller.resultWindow.resultsView.model() is not None
        assert controller.details_dialog is not None
        assert controller.actionQuarantineReceipts in controller.directories_dialog.menuFile.actions()
        application.processEvents()
        options.close()
        controller.prefs.saveGeometry("SavedDetails", controller.details_dialog)
        saved = controller.prefs.get_value("SavedDetails")
        assert all(type(value) is int for value in saved)
        if mode == "picture":
            viewer = controller.details_dialog.selectedImageViewer
            viewer.bestFit = False
            press = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                QPointF(2, 2),
                QPointF(2, 2),
                Qt.MouseButton.MiddleButton,
                Qt.MouseButton.MiddleButton,
                Qt.KeyboardModifier.NoModifier,
            )
            viewer.mousePressEvent(press)
            assert viewer._drag
            release = QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                QPointF(2, 2),
                QPointF(2, 2),
                Qt.MouseButton.MiddleButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            )
            viewer.mouseReleaseEvent(release)
            assert not viewer._drag
        if mode == "standard":
            selected = []
            monkeypatch.setattr(QFileDialog, "exec", lambda self: 1)
            monkeypatch.setattr(QFileDialog, "selectedFiles", lambda self: [str(tmp_path)])
            monkeypatch.setattr(controller.model, "add_directory", selected.append)
            controller.directories_dialog.addFolderTriggered()
            assert selected == [str(tmp_path)]
    finally:
        for widget in application.topLevelWidgets():
            widget.close()


def test_unchecking_result_and_exclusion_rows_accepts_qt6_enum(application):
    from types import SimpleNamespace
    from qt.results_model import ResultsModel
    from qt.exclude_list_table import ExcludeListTable

    row, column = SimpleNamespace(marked=True), SimpleNamespace(name="marked")
    assert ResultsModel._setData(None, row, column, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
    assert row.marked is False
    for model in (ResultsModel, ExcludeListTable):
        for value, expected in ((Qt.CheckState.Checked, True), (2, True), (Qt.CheckState.Unchecked, False), (0, False)):
            assert model._setData(None, row, column, value, Qt.ItemDataRole.CheckStateRole)
            assert row.marked is expected


def test_contents_scan_publishes_review_rows_and_marking(application, tmp_path, monkeypatch):
    from core.scanner import ScanType
    from core.cleanup_plan import EvidenceKind
    from hscommon import desktop
    from hscommon.jobprogress.job import nulljob
    from qt import preferences
    from qt.app import DupeGuru

    monkeypatch.setattr(desktop, "special_folder_path", lambda *args, **kwargs: str(tmp_path / "data"))
    monkeypatch.setattr(
        preferences, "create_qsettings", lambda: QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    files = tmp_path / "files"
    files.mkdir()
    for name in ("one.bin", "two-é.bin"):
        (files / name).write_bytes(b"same scan contents" * 100)
    controller = DupeGuru()
    try:
        monkeypatch.setattr(controller, "confirm", lambda *args, **kwargs: True)
        messages = []
        monkeypatch.setattr(controller, "show_message", messages.append)
        model = controller.model
        model.add_directory(str(files))
        model.options["scan_type"] = ScanType.CONTENTS
        model.options["size_threshold"] = 0

        def complete(jobid, function, args=()):
            function(nulljob, *args)
            model._job_completed(jobid)
            return True

        monkeypatch.setattr(model, "_start_job", complete)
        model.start_scanning()
        assert model.results_scan_type == ScanType.CONTENTS
        assert model._pending_scan_result is None
        assert len(model.results.groups) == 1, messages
        view_model = controller.resultWindow.resultsView.model()
        assert view_model.rowCount(QModelIndex()) == 2
        # Render model roles and toggle the real duplicate row using Qt 6 values.
        index = view_model.index(1, 0)
        assert view_model.flags(index) & Qt.ItemFlag.ItemIsUserCheckable
        assert view_model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        assert model.results.mark_count == 1
        plan = model.build_cleanup_plan()
        assert plan.candidates[0].evidence == EvidenceKind.EXACT_CONTENT
        assert plan.candidates[0].path.exists()
        assert view_model.setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        assert model.results.mark_count == 0
        application.processEvents()
    finally:
        for widget in application.topLevelWidgets():
            widget.close()


def test_real_picture_details_zoom_pan_wheel_and_swap(application, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from PyQt6.QtCore import Qt, QSettings, QEvent, QPoint, QPointF
    from PyQt6.QtGui import QImage, QColor, QPixmap, QMouseEvent, QWheelEvent
    from qt import preferences
    from qt.app import DupeGuru
    from core.app import AppMode
    from hscommon import desktop
    import sys

    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda *error: errors.append(error))
    monkeypatch.setattr(desktop, "special_folder_path", lambda *args, **kw: str(tmp_path / "data"))
    monkeypatch.setattr(
        preferences, "create_qsettings", lambda: QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    ctrl = DupeGuru()
    try:
        ctrl.model.app_mode = AppMode.PICTURE
        ctrl.model._recreate_result_table()
        detail = ctrl.details_dialog
        paths = []
        for name, color in [("ref", QColor(220, 30, 50)), ("dupe", QColor(30, 160, 70))]:
            image = QImage(700, 600, QImage.Format.Format_RGB888)
            image.fill(color)
            path = tmp_path / (name + ".png")
            assert image.save(str(path))
            paths.append(SimpleNamespace(path=path, dimensions=(700, 600)))
        viewer = detail.selectedImageViewer
        other = detail.referenceImageViewer
        vc = detail.vController
        vc.updateView(paths[0], paths[1], object())
        vc.zoomNormalSize()
        vc.zoomIn()
        assert viewer.current_scale == other.current_scale == 1.25
        pressed = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(60, 60),
            QPointF(60, 60),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )
        moved = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(40, 40),
            QPointF(40, 40),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )
        released = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(40, 40),
            QPointF(40, 40),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        viewer.mousePressEvent(pressed)
        viewer.mouseMoveEvent(moved)
        viewer.mouseReleaseEvent(released)
        assert not viewer._drag
        assert viewer.horizontalScrollBar().value() == other.horizontalScrollBar().value()
        wheel = QWheelEvent(
            QPointF(50, 50),
            QPointF(50, 50),
            QPoint(),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate,
            False,
        )
        viewer.wheelEvent(wheel)
        assert viewer.current_scale == other.current_scale == 1.5625
        first = viewer._pixmap.toImage().pixelColor(0, 0)
        vc.swapImages()
        assert other._pixmap.toImage().pixelColor(0, 0) == first
        surface = QPixmap(detail.size())
        detail.render(surface)
        vc.zoomBestFit()
        assert viewer.bestFit and other.bestFit
        assert not errors, errors
    finally:
        for widget in application.topLevelWidgets():
            widget.close()
