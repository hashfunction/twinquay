import errno
import json
from pathlib import Path

import pytest

from core.cleanup_plan import CleanupCandidate, CleanupPlan, EvidenceKind
from core import quarantine


def exact_plan(tmp_path, count=1):
    reference = tmp_path / "keep-参考.bin"
    reference.write_bytes(b"same contents" * 1000)
    candidates = []
    for i in range(count):
        duplicate = tmp_path / f"duplicate-{i}-é.bin"
        duplicate.write_bytes(reference.read_bytes())
        candidates.append(CleanupCandidate.capture(duplicate, reference, EvidenceKind.EXACT_CONTENT))
    return CleanupPlan.create(candidates)


def test_quarantine_and_reload_restore_unicode_bytes(tmp_path):
    plan = exact_plan(tmp_path)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    original = plan.candidates[0].path
    assert receipt.items[0].status == "quarantined"
    assert not original.exists()
    assert plan.candidates[0].reference_path.exists()
    assert json.loads(receipt.receipt_path.read_text())["plan"] == json.loads(json.dumps(plan.to_dict()))
    restored = quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
    assert restored.items[0].status == "restored"
    assert original.read_bytes() == plan.candidates[0].reference_path.read_bytes()


def test_changed_candidate_stays_in_place(tmp_path):
    plan = exact_plan(tmp_path)
    plan.candidates[0].path.write_bytes(b"changed")
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert receipt.items[0].status == "changed_since_plan"
    assert plan.candidates[0].path.read_bytes() == b"changed"


def test_restore_collision_does_not_overwrite_and_can_retry(tmp_path):
    plan = exact_plan(tmp_path)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    original = plan.candidates[0].path
    original.write_bytes(b"new owner")
    result = quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
    assert result.items[0].status == "restore_collision"
    assert original.read_bytes() == b"new owner"
    original.unlink()
    assert quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id]).items[0].status == "restored"


def test_cancellation_after_first_item_keeps_remaining_originals(tmp_path):
    plan = exact_plan(tmp_path, 3)
    calls = iter([False, True, True])
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: next(calls))
    assert [i.status for i in receipt.items] == ["quarantined", "cancelled", "cancelled"]
    assert all(c.path.exists() for c in plan.candidates[1:])
    assert quarantine.load_receipt(receipt.receipt_path).items[0].status == "quarantined"


def test_cross_device_copy_is_verified_before_source_removal(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    original_move = quarantine.move_no_replace

    def cross_device(source, dest):
        if source == plan.candidates[0].path:
            raise OSError(errno.EXDEV, "simulated volume boundary")
        return original_move(source, dest)

    monkeypatch.setattr(quarantine, "move_no_replace", cross_device)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert receipt.items[0].status == "quarantined"
    assert receipt.items[0].transfer == "copy"
    assert not plan.candidates[0].path.exists()
    assert quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id]).items[0].status == "restored"


def test_failed_source_unlink_keeps_verified_payload_and_original(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    original_move = quarantine.move_no_replace

    def cross_device(source, dest):
        if source == plan.candidates[0].path:
            raise OSError(errno.EXDEV, "volume")
        return original_move(source, dest)

    def readonly(*args):
        raise PermissionError("locked source")

    monkeypatch.setattr(quarantine, "move_no_replace", cross_device)
    monkeypatch.setattr(quarantine, "remove_verified_source", readonly)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert receipt.items[0].status == "source_retained"
    assert plan.candidates[0].path.exists()
    assert quarantine.payload_path(receipt, receipt.items[0]).read_bytes() == plan.candidates[0].path.read_bytes()


def test_copy_error_never_removes_source(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)

    def cross_device(source, dest):
        raise OSError(errno.EXDEV, "volume")

    def disk_full(*args):
        raise OSError(errno.ENOSPC, "disk full")

    monkeypatch.setattr(quarantine, "move_no_replace", cross_device)
    monkeypatch.setattr(quarantine, "copy_verified", disk_full)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert receipt.items[0].status == "failed"
    assert plan.candidates[0].path.exists()


def test_modified_payload_is_not_restored(tmp_path):
    receipt = quarantine.execute_plan(exact_plan(tmp_path), tmp_path / "quarantine", lambda: False)
    quarantine.payload_path(receipt, receipt.items[0]).write_bytes(b"corrupted")
    result = quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
    assert result.items[0].status == "payload_changed"
    assert not Path(receipt.items[0].original_path).exists()


def test_interrupted_moved_item_is_discoverable_and_restorable(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    checkpoint = quarantine.checkpoint

    def interrupt(receipt):
        if receipt.items[0].status == "quarantined":
            raise KeyboardInterrupt("power interruption after move")
        checkpoint(receipt)

    monkeypatch.setattr(quarantine, "checkpoint", interrupt)
    with pytest.raises(KeyboardInterrupt):
        quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    monkeypatch.setattr(quarantine, "checkpoint", checkpoint)
    path = tmp_path / "quarantine" / plan.plan_id / "receipt.json"
    receipt = quarantine.load_receipt(path)
    result = quarantine.restore_receipt(path, [receipt.items[0].item_id])
    assert result.items[0].status == "restored"
    assert plan.candidates[0].path.exists()


def test_duplicate_plan_execution_never_overwrites_quarantine(tmp_path):
    plan = exact_plan(tmp_path)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    with pytest.raises(FileExistsError):
        quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert quarantine.payload_path(receipt, receipt.items[0]).exists()


def test_receipt_rejects_payload_path_traversal(tmp_path):
    receipt = quarantine.execute_plan(exact_plan(tmp_path), tmp_path / "quarantine", lambda: False)
    data = json.loads(receipt.receipt_path.read_text())
    data["items"][0]["item_id"] = "../../outside"
    receipt.receipt_path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        quarantine.load_receipt(receipt.receipt_path)


def test_reference_selected_for_removal_is_refused(tmp_path):
    plan = exact_plan(tmp_path, 2)
    first, second = plan.candidates
    candidates = [first, CleanupCandidate.capture(first.reference_path, second.path, EvidenceKind.EXACT_CONTENT)]
    plan = CleanupPlan.create(candidates)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert all(i.status == "reference_in_plan" for i in receipt.items)
    assert all(c.path.exists() for c in plan.candidates)


def test_dangling_link_restore_collision_is_not_overwritten(tmp_path):
    plan = exact_plan(tmp_path)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    original = plan.candidates[0].path
    try:
        original.symlink_to(tmp_path / "nonexistent")
    except OSError:
        pytest.skip("Symlinks require platform permission")
    result = quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
    assert result.items[0].status == "restore_collision"
    assert original.is_symlink()


def test_move_failure_still_writes_receipt_and_leaves_input(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)

    def locked(*args):
        raise PermissionError("locked file")

    monkeypatch.setattr(quarantine, "move_no_replace", locked)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert receipt.items[0].status == "failed"
    assert plan.candidates[0].path.exists()
    assert quarantine.load_receipt(receipt.receipt_path).items[0].detail == "locked file"


def test_payload_publish_collision_keeps_both_files(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    move = quarantine.move_no_replace

    def occupy_target(source, destination):
        if source.name == ".staging":
            destination.write_bytes(b"occupied")
        return move(source, destination)

    monkeypatch.setattr(quarantine, "move_no_replace", occupy_target)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    item = receipt.items[0]
    assert item.status == "recovery_required"
    assert quarantine.payload_path(receipt, item).read_bytes() == b"occupied"
    assert quarantine._staging_path(receipt, item).read_bytes() == plan.candidates[0].reference_path.read_bytes()


def test_receipt_failure_before_move_keeps_original(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    checkpoint = quarantine.checkpoint

    def full_disk(receipt):
        if receipt.items[0].status == "moving":
            raise OSError(errno.ENOSPC, "receipt disk full")
        checkpoint(receipt)

    monkeypatch.setattr(quarantine, "checkpoint", full_disk)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert plan.candidates[0].path.exists()
    assert receipt.items[0].status == "failed"


def test_change_between_validation_and_move_returns_changed_file(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    move = quarantine.move_no_replace
    original = plan.candidates[0].path

    def modify_during_move(source, destination):
        if source == original:
            source.write_bytes(b"new contents while moving")
        return move(source, destination)

    monkeypatch.setattr(quarantine, "move_no_replace", modify_during_move)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine", lambda: False)
    assert receipt.items[0].status == "changed_since_plan"
    assert original.read_bytes() == b"new contents while moving"


def test_final_source_removal_refuses_change(tmp_path):
    plan = exact_plan(tmp_path)
    candidate = plan.candidates[0]
    expected = quarantine.digest(candidate.path)
    candidate.path.write_bytes(b"changed after copy")
    with pytest.raises(ValueError):
        quarantine.remove_verified_source(candidate, expected)
    assert candidate.path.read_bytes() == b"changed after copy"


def test_changed_payload_during_restore_is_returned_to_quarantine(tmp_path, monkeypatch):
    plan = exact_plan(tmp_path)
    receipt = quarantine.execute_plan(plan, tmp_path / "quarantine")
    payload = quarantine.payload_path(receipt, receipt.items[0])
    move = quarantine.move_no_replace

    def mutate_payload(source, destination):
        if source == payload:
            source.write_bytes(b"changed during restore")
        return move(source, destination)

    monkeypatch.setattr(quarantine, "move_no_replace", mutate_payload)
    restored = quarantine.restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
    assert restored.items[0].status == "payload_changed"
    assert not plan.candidates[0].path.exists()
    assert payload.read_bytes() == b"changed during restore"
