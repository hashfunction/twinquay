# Copyright 2026 Trieflow LLC. GPL-3.0; see LICENSE.
"""Immutable discovery evidence; only a fresh full byte comparison permits cleanup."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import os
from pathlib import Path
import stat
from uuid import uuid4


class EvidenceKind(str, Enum):
    EXACT_CONTENT = "exact_content"
    SIMILARITY = "similarity"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def path_key(path):
    return os.path.normcase(os.path.abspath(path))


def safe_path(path):
    """Reject links/reparse points, including ancestors and cloud placeholders."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        info = part.lstat()
        attributes = getattr(info, "st_file_attributes", 0)
        # REPARSE_POINT, OFFLINE, RECALL_ON_OPEN, RECALL_ON_DATA_ACCESS.
        if stat.S_ISLNK(info.st_mode) or attributes & (0x400 | 0x1000 | 0x40000 | 0x400000):
            raise ValueError(f"Link, reparse point or placeholder: {part}")
    return path


def has_extra_streams(path):
    """Refuse named NTFS streams instead of silently dropping metadata on copy.

    FindFirstStreamW/FindNextStreamW enumerate $DATA streams; unknown errors
    fail closed. Native Windows acceptance is required for this boundary.
    """
    if os.name != "nt":
        return bool(os.listxattr(path)) if hasattr(os, "listxattr") else False
    import ctypes
    from ctypes import wintypes

    class StreamData(ctypes.Structure):
        _fields_ = [("size", ctypes.c_longlong), ("name", wintypes.WCHAR * 296)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    first = kernel.FindFirstStreamW
    first.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(StreamData), wintypes.DWORD]
    first.restype = wintypes.HANDLE
    next_stream = kernel.FindNextStreamW
    next_stream.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]
    next_stream.restype = wintypes.BOOL
    close = kernel.FindClose
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    data = StreamData()
    handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()
        if error in (38, 87):  # No streams / filesystem does not support streams.
            return False
        raise ctypes.WinError(error)
    try:
        while True:
            if data.name != "::$DATA":
                return True
            if not next_stream(handle, ctypes.byref(data)):
                error = ctypes.get_last_error()
                if error != 38:
                    raise ctypes.WinError(error)
                return False
    finally:
        close(handle)


def signature(info):
    return (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_dev, info.st_ino)


def file_signature(path):
    """Use one metadata API for the named file and its open read handle.

    CPython 3.12 on Windows exposes creation time in path stat's st_ctime,
    but ChangeTime in fstat. Reading every identity from a descriptor preserves
    the full change-time check across rename, copy and final deletion.
    """
    path = safe_path(path)
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Not a regular file")
        return signature(info)


@dataclass(frozen=True)
class CleanupCandidate:
    path: Path
    reference_path: Path
    evidence: EvidenceKind
    candidate_size: int
    candidate_mtime_ns: int
    reference_size: int
    reference_mtime_ns: int
    candidate_identity: tuple = ()
    reference_identity: tuple = ()

    @classmethod
    def capture(cls, path, reference_path, evidence):
        path, reference_path = Path(os.path.abspath(path)), Path(os.path.abspath(reference_path))

        def snapshot(p):
            try:
                return file_signature(p)
            except (OSError, ValueError):
                return (-1, -1, -1, -1, -1)

        left, right = snapshot(path), snapshot(reference_path)
        return cls(path, reference_path, evidence, left[0], left[1], right[0], right[1], left, right)


@dataclass(frozen=True)
class CleanupPlan:
    version: int
    plan_id: str
    created_at: str
    candidates: tuple[CleanupCandidate, ...]

    @classmethod
    def create(cls, candidates):
        return cls(1, str(uuid4()), timestamp(), tuple(sorted(candidates, key=lambda c: path_key(c.path))))

    def to_dict(self):
        result = asdict(self)
        for candidate in result["candidates"]:
            candidate["path"] = str(candidate["path"])
            candidate["reference_path"] = str(candidate["reference_path"])
            candidate["evidence"] = candidate["evidence"].value
        return result

    @classmethod
    def from_dict(cls, value):
        if value["version"] != 1:
            raise ValueError("Unsupported cleanup plan version")
        candidates = []
        for item in value["candidates"]:
            data = dict(item)
            data["path"], data["reference_path"] = Path(data["path"]), Path(data["reference_path"])
            data["evidence"] = EvidenceKind(data["evidence"])
            for key in ("candidate_identity", "reference_identity"):
                data[key] = tuple(data.get(key, ()))
            candidates.append(CleanupCandidate(**data))
        return cls(1, value["plan_id"], value["created_at"], tuple(candidates))


@dataclass(frozen=True)
class Eligibility:
    code: str
    detail: str = ""

    @property
    def eligible(self):
        return self.code == "eligible"


def files_equal(left: Path, right: Path, chunk_size: int = 1024 * 1024) -> bool:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    safe_path(left)
    safe_path(right)
    with open(left, "rb") as a, open(right, "rb") as b:
        before = (signature(os.fstat(a.fileno())), signature(os.fstat(b.fileno())))
        if not all(stat.S_ISREG(os.fstat(f.fileno()).st_mode) for f in (a, b)):
            return False
        while True:
            first, second = a.read(chunk_size), b.read(chunk_size)
            if first != second:
                return False
            if not first:
                after = (signature(os.fstat(a.fileno())), signature(os.fstat(b.fileno())))
                return before == after == (file_signature(left), file_signature(right))


def validate_candidate(candidate, compare=True):
    if candidate.evidence != EvidenceKind.EXACT_CONTENT:
        return Eligibility("similarity_only", "Run a Contents scan to create exact-content candidates.")
    try:
        left, right = safe_path(candidate.path), safe_path(candidate.reference_path)
        a, b = left.lstat(), right.lstat()
        if not all(stat.S_ISREG(i.st_mode) for i in (a, b)):
            return Eligibility("not_regular_file")
        if has_extra_streams(left) or has_extra_streams(right):
            return Eligibility("extra_file_metadata", "Named streams or extended attributes require manual review.")
        if path_key(left) == path_key(right) or os.path.samestat(a, b):
            return Eligibility("same_file")
        if not a.st_mode & stat.S_IWUSR or getattr(a, "st_file_attributes", 0) & 1:
            return Eligibility("read_only")
        if (a.st_size, a.st_mtime_ns, b.st_size, b.st_mtime_ns) != (
            candidate.candidate_size,
            candidate.candidate_mtime_ns,
            candidate.reference_size,
            candidate.reference_mtime_ns,
        ):
            return Eligibility("changed_since_plan")
        left_identity, right_identity = file_signature(left), file_signature(right)
        if (candidate.candidate_identity and left_identity != candidate.candidate_identity) or (
            candidate.reference_identity and right_identity != candidate.reference_identity
        ):
            return Eligibility("changed_since_plan")
        if compare and not files_equal(left, right):
            return Eligibility("not_equal")
        # Recheck metadata after the full read, including path replacement.
        if left_identity != file_signature(left) or right_identity != file_signature(right):
            return Eligibility("changed_since_plan")
        return Eligibility("eligible")
    except FileNotFoundError as exc:
        return Eligibility("missing", str(exc))
    except ValueError as exc:
        return Eligibility("unsafe_path", str(exc))
    except OSError as exc:
        return Eligibility("failed", str(exc))
