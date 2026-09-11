# Copyright 2026 Trieflow LLC. GPL-3.0; see LICENSE.
"""User-selected quarantine with write-ahead receipts and no-replace recovery.

Receipts record intended paths and hashes before any source can be removed.
Never delete a payload automatically, including after an error. Unknown or partial
states remain inspectable and recovery validates bytes before changing paths.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from uuid import UUID, uuid4, uuid5

from core.cleanup_plan import (
    CleanupCandidate,
    CleanupPlan,
    EvidenceKind,
    files_equal,
    path_key,
    safe_path,
    signature,
    timestamp,
    validate_candidate,
)


@dataclass
class ReceiptItem:
    item_id: str
    original_path: str
    name: str
    status: str = "pending"
    detail: str = ""
    size: int = 0
    sha256: str = ""
    transfer: str = ""


@dataclass
class CleanupReceipt:
    receipt_path: Path
    plan: CleanupPlan
    items: list[ReceiptItem]
    updated_at: str = ""

    def to_dict(self):
        return dict(
            version=1, plan=self.plan.to_dict(), updated_at=self.updated_at, items=[asdict(item) for item in self.items]
        )


RestoreReceipt = CleanupReceipt


def _fsync_directory(path):
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def checkpoint(receipt):
    receipt.updated_at = timestamp()
    safe_path(receipt.receipt_path.parent)
    temp = receipt.receipt_path.with_name(f"receipt.{uuid4()}.tmp")
    with temp.open("x", encoding="utf-8") as stream:
        json.dump(receipt.to_dict(), stream, ensure_ascii=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, receipt.receipt_path)
    _fsync_directory(receipt.receipt_path.parent)


def load_receipt(receipt_path):
    receipt_path = safe_path(Path(receipt_path))
    with receipt_path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if data["version"] != 1:
        raise ValueError("Unsupported receipt version")
    plan = CleanupPlan.from_dict(data["plan"])
    UUID(plan.plan_id)
    items = [ReceiptItem(**item) for item in data["items"]]
    if len({i.item_id for i in items}) != len(items):
        raise ValueError("Duplicate receipt item identifier")
    expected_items = {candidate_item_id(plan, c): c for c in plan.candidates}
    for item in items:
        UUID(item.item_id)
        if item.item_id not in expected_items or item.original_path != str(expected_items[item.item_id].path):
            raise ValueError("Receipt item does not match its original plan")
        if Path(item.name).name != item.name or item.name in ("", ".", "..") or "/" in item.name or "\\" in item.name:
            raise ValueError("Invalid payload name")
        if not Path(item.original_path).is_absolute():
            raise ValueError("Original path must be absolute")
    return CleanupReceipt(receipt_path, plan, items, data["updated_at"])


def candidate_item_id(plan, candidate):
    return str(uuid5(UUID(plan.plan_id), path_key(candidate.path)))


def payload_path(receipt, item):
    return receipt.receipt_path.parent / "payload" / item.item_id / item.name


def _staging_path(receipt, item):
    return payload_path(receipt, item).with_name(".staging")


@contextmanager
def receipt_lock(directory):
    """OS-owned lock releases even on process death; the harmless lock file stays."""
    safe_path(directory)
    lockpath = directory / ".lock"
    if lockpath.exists():
        safe_path(lockpath)
    with lockpath.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def digest(path):
    safe_path(path)
    with path.open("rb") as stream:
        before = signature(os.fstat(stream.fileno()))
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Not a regular file")
        value = hashlib.file_digest(stream, "sha256").hexdigest()
        if before != signature(os.fstat(stream.fileno())) or before != signature(path.lstat()):
            raise ValueError("File changed during read")
        return before[0], value


def move_no_replace(source, destination):
    """Never use replace/rename-overwrite for a user file."""
    safe_path(source)
    safe_path(destination.parent)
    if os.name == "nt":
        # Windows rename fails if the target exists, including a dangling link.
        os.rename(source, destination)
    else:
        os.link(source, destination, follow_symlinks=False)
        source.unlink()
    _fsync_directory(destination.parent)
    _fsync_directory(source.parent)


def copy_verified(source, destination, expected):
    safe_path(source)
    safe_path(destination.parent)
    before = signature(source.lstat())
    with source.open("rb") as src, destination.open("xb") as dst:
        if signature(os.fstat(src.fileno())) != before:
            raise ValueError("Source replaced before copy")
        while chunk := src.read(1024 * 1024):
            dst.write(chunk)
        dst.flush()
        os.fsync(dst.fileno())
        if signature(os.fstat(src.fileno())) != before:
            raise ValueError("Source changed during copy")
    if before != signature(source.lstat()) or digest(source) != expected or digest(destination) != expected:
        raise ValueError("Copy verification failed; source retained")
    shutil.copystat(source, destination, follow_symlinks=False)
    _fsync_directory(destination.parent)


def remove_verified_source(candidate, expected):
    """Final cross-volume removal; Windows denies writers and deletes the checked handle.

    No path-based unlink is used on Windows after verification. The native API
    path must be exercised by the Windows filesystem acceptance tests.
    """
    check = validate_candidate(candidate)
    if not check.eligible or digest(candidate.path) != expected:
        raise ValueError("Source changed after copy; both files retained")
    if os.name != "nt":
        # POSIX is a development/test host, not the released Windows product.
        candidate.path.unlink()
        return
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    # GENERIC_READ | DELETE; exclusive sharing; OPEN_EXISTING; OPEN_REPARSE_POINT.
    handle = create(str(candidate.path), 0x80000000 | 0x10000, 0, None, 3, 0x200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if candidate.candidate_identity and signature(info) != candidate.candidate_identity:
            raise ValueError("Source changed before exclusive access; both files retained")
        safe_path(candidate.reference_path)
        with candidate.reference_path.open("rb") as reference:
            before = signature(os.fstat(reference.fileno()))
            if candidate.reference_identity and before != candidate.reference_identity:
                raise ValueError("Reference changed before final byte comparison")
            while True:
                left, right = source.read(1024 * 1024), reference.read(1024 * 1024)
                if left != right:
                    raise ValueError("Source and reference differ; source retained")
                if not left:
                    break
            if before != signature(os.fstat(reference.fileno())) or before != signature(
                candidate.reference_path.stat()
            ):
                raise ValueError("Reference changed during final byte comparison")
        disposition = kernel.SetFileInformationByHandle
        disposition.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        disposition.restype = wintypes.BOOL
        delete_file = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO contains BOOLEAN, not BOOL.
        if not disposition(handle, 4, ctypes.byref(delete_file), ctypes.sizeof(delete_file)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Closing this exact handle commits deletion; no replaced path can be unlinked.


def execute_plan(plan, quarantine_root, cancel=lambda: False, progress=lambda done, total, path: None):
    UUID(plan.plan_id)
    if len({path_key(c.path) for c in plan.candidates}) != len(plan.candidates):
        raise ValueError("A candidate may occur only once in a plan")
    candidate_paths = {path_key(c.path) for c in plan.candidates}
    references_selected = any(path_key(c.reference_path) in candidate_paths for c in plan.candidates)
    root = Path(os.path.abspath(quarantine_root))
    root.mkdir(parents=True, exist_ok=True)
    safe_path(root)
    directory = root / plan.plan_id
    directory.mkdir()  # A plan is executed once. Never reuse/overwrite a receipt.
    receipt = CleanupReceipt(
        directory / "receipt.json",
        plan,
        [ReceiptItem(candidate_item_id(plan, c), str(c.path), c.path.name) for c in plan.candidates],
    )
    with receipt_lock(directory):
        checkpoint(receipt)
        # Store the original plan separately as an inspectable, immutable preview.
        with (directory / "plan.json").open("x", encoding="utf-8") as stream:
            json.dump(plan.to_dict(), stream, ensure_ascii=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        cancelled = False
        for index, (candidate, item) in enumerate(zip(plan.candidates, receipt.items)):
            cancelled = cancelled or cancel()
            if cancelled:
                item.status = "cancelled"
                checkpoint(receipt)
                continue
            progress(index, len(receipt.items), candidate.path)
            if references_selected:
                item.status = "reference_in_plan"
                item.detail = "This plan also selects a reference for removal; review and create a new plan."
                checkpoint(receipt)
                continue
            eligibility = validate_candidate(candidate)
            if not eligibility.eligible:
                item.status, item.detail = eligibility.code, eligibility.detail
                checkpoint(receipt)
                continue
            payload = payload_path(receipt, item)
            staging = _staging_path(receipt, item)
            try:
                payload.parent.mkdir(parents=True)
                safe_path(payload.parent)
                item.size, item.sha256 = digest(candidate.path)
                expected = (item.size, item.sha256)
                # Hashing is not authorization: repeat full pair validation after hashing.
                eligibility = validate_candidate(candidate)
                if not eligibility.eligible:
                    item.status, item.detail = eligibility.code, eligibility.detail
                    checkpoint(receipt)
                    continue
                item.status = "moving"
                item.transfer = "move"
                checkpoint(receipt)  # Durable intent before removing any source path.
                try:
                    move_no_replace(candidate.path, staging)
                except OSError as exc:
                    if exc.errno != errno.EXDEV:
                        raise
                    item.transfer = "copy"
                    item.status = "copying"
                    checkpoint(receipt)
                    copy_verified(candidate.path, staging, expected)
                if digest(staging) != expected or not files_equal(staging, candidate.reference_path):
                    if item.transfer == "move":
                        move_no_replace(staging, candidate.path)
                        item.status = "changed_since_plan"
                        item.detail = "File changed during move; returned to its original path."
                        checkpoint(receipt)
                        continue
                    raise ValueError("Copied bytes no longer match reference; original and staging retained")
                move_no_replace(staging, payload)
                if item.transfer == "copy":
                    item.status = "source_retained"
                    checkpoint(receipt)  # A verified second copy exists before unlink.
                    check = validate_candidate(candidate)
                    if not check.eligible:
                        item.detail = f"{check.code}; source and payload retained"
                        checkpoint(receipt)
                        continue
                    try:
                        remove_verified_source(candidate, expected)
                        _fsync_directory(candidate.path.parent)
                    except (OSError, ValueError) as exc:
                        item.detail = str(exc)
                        checkpoint(receipt)
                        continue
                item.status = "quarantined"
                item.detail = ""
            except (OSError, ValueError) as exc:
                item.status = "recovery_required" if payload.exists() or staging.exists() else "failed"
                item.detail = str(exc)
            checkpoint(receipt)
        progress(len(receipt.items), len(receipt.items), directory)
    return receipt


def restore_receipt(receipt_path, item_ids, cancel=lambda: False, progress=lambda done, total, path: None):
    receipt_path = Path(receipt_path)
    with receipt_lock(safe_path(receipt_path.parent)):
        receipt = load_receipt(receipt_path)
        chosen = set(item_ids)
        if not chosen <= {i.item_id for i in receipt.items}:
            raise ValueError("Unknown receipt item")
        for index, item in enumerate(receipt.items):
            if item.item_id not in chosen or cancel():
                continue
            original = Path(item.original_path)
            progress(index, len(receipt.items), original)
            if not item.sha256:
                continue
            payload, staging = payload_path(receipt, item), _staging_path(receipt, item)
            source = payload if payload.exists() else staging
            expected = (item.size, item.sha256)
            try:
                safe_path(original.parent)  # Refuse renamed/reparse parents; user can recover manually.
                if os.path.lexists(original):
                    if item.status == "restoring" and not source.exists() and digest(original) == expected:
                        item.status = "restored"
                    elif item.status != "restored":
                        item.status = "restore_collision"
                        item.detail = "Original path is occupied; existing file was kept."
                    checkpoint(receipt)
                    continue
                if not source.exists():
                    item.status = "missing_payload"
                    checkpoint(receipt)
                    continue
                if digest(source) != expected:
                    item.status = "payload_changed"
                    item.detail = "Payload hash/size changed; no file restored."
                    checkpoint(receipt)
                    continue
                item.status = "restoring"
                checkpoint(receipt)
                try:
                    move_no_replace(source, original)
                except OSError as exc:
                    if exc.errno != errno.EXDEV:
                        raise
                    # Private restore staging beside the original, atomically published without replacement.
                    restore_temp = original.with_name(f".twinquay-restore-{uuid4()}")
                    item.detail = f"Restore staging: {restore_temp}"
                    checkpoint(receipt)
                    copy_verified(source, restore_temp, expected)
                    move_no_replace(restore_temp, original)
                    if digest(original) != expected:
                        raise ValueError("Restored copy verification failed; quarantine retained")
                    remove_verified_source(
                        CleanupCandidate.capture(source, original, EvidenceKind.EXACT_CONTENT), expected
                    )
                if digest(original) != expected:
                    move_no_replace(original, source)
                    item.status = "payload_changed"
                    item.detail = "Payload changed during restore; returned to quarantine."
                    checkpoint(receipt)
                    continue
                item.status = "restored"
                item.detail = ""
            except FileExistsError as exc:
                item.status, item.detail = "restore_collision", str(exc)
            except (OSError, ValueError) as exc:
                item.status, item.detail = "restore_failed", str(exc)
            checkpoint(receipt)
    return receipt
