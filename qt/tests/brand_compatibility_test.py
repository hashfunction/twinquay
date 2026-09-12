"""Use actual QSettings files to prove renamed Windows/portable data continuity."""
import os
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication


@pytest.fixture
def windows_settings(tmp_path, monkeypatch):
    from qt import util

    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    application = QApplication.instance() or QApplication([])
    previous = application.applicationName()
    application.setApplicationName('DupliSift')
    monkeypatch.setattr(util, 'ISWINDOWS', True)
    monkeypatch.setattr(util, 'executable_folder', lambda: str(tmp_path / 'portable'))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    (tmp_path / 'portable').mkdir()
    yield util, tmp_path
    application.setApplicationName(previous)


def seed(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    settings.setValue('Language', value)
    settings.sync()


def test_existing_windows_settings_and_data_remain_at_the_legacy_path(windows_settings):
    util, root = windows_settings
    path = root / 'local/TwinQuay/settings.ini'
    seed(path, 'fr')
    settings = util.create_qsettings()
    assert Path(settings.fileName()) == path
    assert settings.value('Language') == 'fr'
    assert settings.value('Portable', type=bool) is False
    assert Path(util.get_appdata()) == path.parent
    assert not (root / 'local/DupliSift').exists()


@pytest.mark.parametrize('name', ['DupliSift.ini', 'TwinQuay.ini'])
def test_new_and_legacy_portable_settings_keep_existing_data(windows_settings, name):
    util, root = windows_settings
    path = root / 'portable' / name
    seed(path, 'de')
    settings = util.create_qsettings()
    assert Path(settings.fileName()) == path
    assert settings.value('Language') == 'de'
    assert settings.value('Portable', type=bool) is True
    assert Path(util.get_appdata(portable=True)) == root / 'portable/data/TwinQuay'


def test_legacy_portable_settings_take_precedence_when_both_files_exist(windows_settings):
    util, root = windows_settings
    legacy = root / 'portable/TwinQuay.ini'
    fresh = root / 'portable/DupliSift.ini'
    seed(legacy, 'fr')
    seed(fresh, 'de')
    before = fresh.read_bytes()
    settings = util.create_qsettings()
    assert Path(settings.fileName()) == legacy
    assert settings.value('Language') == 'fr'
    assert fresh.read_bytes() == before
