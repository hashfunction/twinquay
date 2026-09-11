"""Real-file regressions for the Python 3.12 Windows stat/fstat boundary."""

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import cleanup_plan, quarantine


def duplicate_pair(tmp_path):
    left, right = tmp_path / "duplicate-é.bin", tmp_path / "reference.bin"
    left.write_bytes(b"exact contents\r\n" * 1000)
    right.write_bytes(left.read_bytes())
    return left, right


def test_renamed_file_digest_and_byte_check_remain_valid(tmp_path):
    left, right = duplicate_pair(tmp_path)
    expected = len(left.read_bytes()), hashlib.sha256(left.read_bytes()).hexdigest()
    staged = tmp_path / ".staging"
    os.rename(left, staged)
    assert quarantine.digest(staged) == expected
    assert cleanup_plan.files_equal(staged, right)


@pytest.fixture
def path_birthtime_semantics(tmp_path, monkeypatch):
    """Emulate the measured 3.12 Windows path-stat API, keeping real fstat/bytes.

    CPython's win32_xstat exposes creation time as st_ctime, whereas its fstat
    exposes ChangeTime. Only the path observation is substituted; every open,
    read, rename, copy, receipt and restore still uses real temporary files.
    """
    lstat = Path.lstat

    def creation_time_stat(path, *args, **kwargs):
        info = lstat(path, *args, **kwargs)
        if path.parent == tmp_path or tmp_path in path.parents:
            values = {key: getattr(info, key) for key in dir(info) if key.startswith("st_")}
            values["st_ctime_ns"] = 1_600_000_000_000_000_000
            return SimpleNamespace(**values)
        return info

    monkeypatch.setattr(Path, "lstat", creation_time_stat)


def test_path_birthtime_does_not_conflict_with_handle_change_time(tmp_path, path_birthtime_semantics):
    left, right = duplicate_pair(tmp_path)
    candidate = cleanup_plan.CleanupCandidate.capture(left, right, cleanup_plan.EvidenceKind.EXACT_CONTENT)
    assert cleanup_plan.files_equal(left, right)
    assert cleanup_plan.validate_candidate(candidate).eligible
    receipt = quarantine.execute_plan(cleanup_plan.CleanupPlan.create([candidate]), tmp_path / "quarantine")
    assert receipt.items[0].status == "quarantined"
    restored = quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
    assert restored.items[0].status == "restored"
    assert left.read_bytes() == right.read_bytes()


def test_full_handle_change_time_is_still_checked(tmp_path, path_birthtime_semantics, monkeypatch):
    left, right = duplicate_pair(tmp_path)
    candidate = cleanup_plan.CleanupCandidate.capture(left, right, cleanup_plan.EvidenceKind.EXACT_CONTENT)
    fstat = os.fstat
    with left.open("rb") as stream:
        identity = fstat(stream.fileno()).st_ino

    def changed_handle(fd):
        info = fstat(fd)
        if info.st_ino == identity:
            values = {key: getattr(info, key) for key in dir(info) if key.startswith("st_")}
            values["st_ctime_ns"] += 100
            return SimpleNamespace(**values)
        return info

    monkeypatch.setattr(os, "fstat", changed_handle)
    # Same bytes, size, mtime, device and inode; change-time alone invalidates.
    assert cleanup_plan.validate_candidate(candidate).code == "changed_since_plan"
    receipt = quarantine.execute_plan(cleanup_plan.CleanupPlan.create([candidate]), tmp_path / "quarantine")
    assert receipt.items[0].status == "changed_since_plan"
    assert left.read_bytes() == right.read_bytes()
