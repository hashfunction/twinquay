import os
from dataclasses import replace

import pytest

from core.cleanup_plan import CleanupCandidate, CleanupPlan, EvidenceKind, files_equal, validate_candidate


def candidate_for(tmp_path, evidence=EvidenceKind.EXACT_CONTENT):
    left, right = tmp_path / "duplicate.bin", tmp_path / "reference.bin"
    left.write_bytes(b"same bytes")
    right.write_bytes(b"same bytes")
    return CleanupCandidate.capture(left, right, evidence)


def test_exact_bytes_are_required(tmp_path):
    c = candidate_for(tmp_path)
    assert validate_candidate(c).code == "eligible"
    assert files_equal(c.path, c.reference_path, chunk_size=2)


def test_similarity_alone_never_authorizes_cleanup_even_for_identical_files(tmp_path):
    assert validate_candidate(candidate_for(tmp_path, EvidenceKind.SIMILARITY)).code == "similarity_only"


@pytest.mark.parametrize("side", ["path", "reference_path"])
def test_content_change_after_plan_is_refused(tmp_path, side):
    c = candidate_for(tmp_path)
    getattr(c, side).write_bytes(b"changed bytes")
    assert validate_candidate(c).code == "changed_since_plan"


def test_same_size_changed_bytes_and_restored_mtime_are_refused(tmp_path):
    c = candidate_for(tmp_path)
    c.path.write_bytes(b"evil bytes")
    os.utime(c.path, ns=(c.candidate_mtime_ns, c.candidate_mtime_ns))
    assert validate_candidate(c).code in ("changed_since_plan", "not_equal")


def test_missing_directory_and_same_file_are_refused(tmp_path):
    c = candidate_for(tmp_path)
    assert validate_candidate(replace(c, reference_path=c.path)).code == "same_file"
    c.path.unlink()
    assert validate_candidate(c).code == "missing"
    c.path.mkdir()
    assert validate_candidate(c).code == "not_regular_file"


def test_symlink_and_symlink_parent_are_refused(tmp_path):
    c = candidate_for(tmp_path)
    c.path.unlink()
    try:
        c.path.symlink_to(c.reference_path)
        parent = tmp_path / "linked"
        parent.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation requires OS permission")
    assert validate_candidate(c).code == "unsafe_path"
    linked = CleanupCandidate.capture(parent / c.reference_path.name, c.reference_path, EvidenceKind.EXACT_CONTENT)
    assert validate_candidate(linked).code == "unsafe_path"


def test_hardlinked_same_file_is_refused(tmp_path):
    c = candidate_for(tmp_path)
    c.path.unlink()
    os.link(c.reference_path, c.path)
    assert validate_candidate(CleanupCandidate.capture(c.path, c.reference_path, c.evidence)).code == "same_file"


def test_read_only_candidate_is_refused(tmp_path):
    c = candidate_for(tmp_path)
    c.path.chmod(0o444)
    try:
        assert validate_candidate(c).code == "read_only"
    finally:
        c.path.chmod(0o600)


def test_plan_serialization_is_stable_and_versioned(tmp_path):
    c = candidate_for(tmp_path)
    plan = CleanupPlan.create([c])
    restored = CleanupPlan.from_dict(plan.to_dict())
    assert restored == plan
    with pytest.raises(ValueError):
        CleanupPlan.from_dict(dict(plan.to_dict(), version=999))


def test_unique_extra_file_metadata_is_not_treated_as_duplicate(tmp_path):
    c = candidate_for(tmp_path)
    if os.name == "nt":
        from pathlib import Path

        Path(str(c.path) + ":twinquay-test").write_bytes(b"unique stream")
    elif hasattr(os, "setxattr"):
        try:
            os.setxattr(c.path, "user.twinquay", b"unique metadata")
        except OSError:
            pytest.skip("Filesystem does not support extended attributes")
    else:
        pytest.skip("No extended metadata API")
    refreshed = CleanupCandidate.capture(c.path, c.reference_path, EvidenceKind.EXACT_CONTENT)
    assert validate_candidate(refreshed).code == "extra_file_metadata"


def test_platform_reports_extra_streams_and_candidate_is_refused(tmp_path, monkeypatch):
    from core import cleanup_plan

    c = candidate_for(tmp_path)
    monkeypatch.setattr(cleanup_plan, "has_extra_streams", lambda path: path == c.path, raising=False)
    assert validate_candidate(c).code == "extra_file_metadata"
