# Copyright 2026 Trieflow LLC. MIT.
"""Independent bytes/JSON oracle for the installed UI workflow; no product imports.

Only prepare writes fixtures. The other commands never move, restore or delete
files: those operations must be performed by the real installed application.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from uuid import UUID, uuid5

# Original fictional project documents, authored for this application's real workflow.
PAIR_BYTES = b"""Cedar House renovation
Project brief | September 2026

Goal
Create a calm, practical workspace in the garden room while retaining the oak
floor and existing window frames. Keep the hallway clear during construction.

Scope
- Repair and repaint the garden room walls in warm white.
- Add adjustable shelving on the north wall for books and project materials.
- Install task lighting above the desk and a dimmable light near the reading chair.
- Reuse the oak table as a shared work surface.

Review before ordering
Confirm shelf dimensions on site. Compare two lighting samples in daylight.
Keep the approved project brief in the project folder; the emailed attachment
contains the same brief and can be reviewed as a duplicate.

Next visit
Measure the north wall, photograph existing joinery, and record socket locations.
"""
CONTROL_BYTES = b"""Cedar House renovation
Site visit notes | September 2026

The garden room faces east and receives direct light in the morning.
The oak floor is sound; retain it and protect it while the walls are repainted.
Check the window latch before specifying any replacement hardware.
The north wall needs a second measurement before shelves are ordered.

These notes are a separate original document and must remain in the project.
"""
ROOMS = (
    "Garden room", "Entrance hall", "Kitchen", "Dining room", "Living room", "Study",
    "Main bedroom", "Guest bedroom", "Bathroom", "Laundry room", "Stair landing", "Covered porch",
)
SURVEY_TASKS = (
    "Measure each finished wall and note any irregular corners before drawing the final furniture layout.",
    "Record the location and height of every socket so the electrician can review access behind furniture.",
    "Check the window frames, latches and seals; retain existing joinery wherever it remains serviceable.",
    "Photograph the floor finish in daylight and identify areas needing protection during repainting work.",
    "Compare warm-white paint samples on two walls and review their appearance in morning and evening light.",
    "List furniture to retain, with width and depth, and check clear walking routes before placing new orders.",
    "Review task and ambient lighting separately; label each proposed fitting and confirm its dimmer support.",
    "Measure storage needs and shelf spacing with the household; keep frequently used items easy to reach.",
    "Identify surfaces that need repair, record the proposed treatment, and seek approval before removal.",
    "Confirm the installation sequence, protect retained materials, and leave a clear access route each day.",
)
SURVEY_BYTES = ("\nRoom survey checklist for the next site visit\n" + "".join(
    f"{room} / {number:02d}: {task}\n"
    for room in ROOMS for number, task in enumerate(SURVEY_TASKS, 1)
)).encode("utf-8")
PAIR_BYTES += SURVEY_BYTES
CONTROL_BYTES += b"\nChecklist reference for the survey team\n" + SURVEY_BYTES
COLLISION_BYTES = b"DupliSift owned restore collision: preserve while handle is held.\n"



def safe(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x441400:
            raise ValueError(f"Link/reparse/placeholder in workflow fixture: {item}")
    return path


def signature(info):
    return (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_dev, info.st_ino)


def open_read(path):
    if os.name != "nt":
        return path.open("rb")
    # Read an owned DeleteOnClose collision without denying the retained writer's
    # write/delete access. This does not acquire cleanup ownership of its pathname.
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
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    handle = create(str(path), 0x80000000, 7, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close(handle)
        raise
    return os.fdopen(descriptor, "rb")


def read(path, limit=1024 * 1024):
    path = safe(path)
    with open_read(path) as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= limit:
            raise ValueError(f"Not a bounded regular file: {path}")
        data = stream.read(limit + 1)
        if len(data) != before.st_size or signature(before) != signature(os.fstat(stream.fileno())):
            raise ValueError(f"File changed while reading: {path}")
        safe(path)
        with open_read(path) as named:
            if signature(before) != signature(os.fstat(named.fileno())):
                raise ValueError(f"File pathname changed while reading: {path}")
    return data, signature(before)


def check_bytes(path, expected):
    data, identity = read(path)
    if data != expected:
        raise ValueError(f"Unexpected workflow bytes: {path}")
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "identity": identity}


def load_json(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value

    return json.loads(read(path, 128 * 1024)[0], object_pairs_hook=unique)


def prepare(root):
    root = safe(root)
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError("Workflow fixture root must be an exclusive empty directory")
    (root / "Project Documents").mkdir()
    (root / "Review Copies").mkdir()
    files = []
    for name, content in (
        ("Cedar House Brief.txt", PAIR_BYTES),
        ("Cedar House Brief - emailed.txt", PAIR_BYTES),
        ("Cedar House Site Notes.txt", CONTROL_BYTES),
    ):
        path = root / "Project Documents" / name
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        files.append(check_bytes(path, content))
    return {
        "sample_provenance": "Original fictional Cedar House project documents, copyright 2026 Trieflow LLC; no customer files.",
        "root": str(root),
        "input": str(root / "Project Documents"),
        "quarantine": str(root / "Review Copies"),
        "plan_path": str(root / "Cedar House - Cleanup Plan.json"),
        "files": files,
        "collision": {"bytes": len(COLLISION_BYTES), "sha256": hashlib.sha256(COLLISION_BYTES).hexdigest()},
    }


def plan_data(root):
    safe(root)
    plan = load_json(root / "Cedar House - Cleanup Plan.json")
    if type(plan.get("version")) is not int or plan["version"] != 1:
        raise ValueError("Unexpected plan version")
    if str(UUID(plan["plan_id"])) != plan["plan_id"] or not isinstance(plan["created_at"], str):
        raise ValueError("Unexpected plan identifier/time")
    candidates = plan.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise ValueError("Expected exactly one selected duplicate")
    candidate = candidates[0]
    if (
        candidate.get("path") != str(root / "Project Documents/Cedar House Brief - emailed.txt")
        or candidate.get("reference_path") != str(root / "Project Documents/Cedar House Brief.txt")
        or candidate.get("evidence") != "exact_content"
    ):
        raise ValueError("Selected plan does not keep the intended exact-content reference")
    for prefix in ("candidate", "reference"):
        identity = candidate.get(prefix + "_identity")
        if (
            type(candidate.get(prefix + "_size")) is not int
            or candidate[prefix + "_size"] != len(PAIR_BYTES)
            or type(candidate.get(prefix + "_mtime_ns")) is not int
            or not isinstance(identity, list)
            or len(identity) != 5
            or any(type(value) is not int for value in identity)
            or identity[0] != len(PAIR_BYTES)
            or identity[1] != candidate[prefix + "_mtime_ns"]
        ):
            raise ValueError("Plan lacks the exact size/full filesystem identity")
    return plan


def inputs(root, duplicate_bytes):
    expected = {"Cedar House Brief.txt", "Cedar House Site Notes.txt"}
    if duplicate_bytes is not None:
        expected.add("Cedar House Brief - emailed.txt")
    directory = safe(root / "Project Documents")
    if {p.name for p in directory.iterdir()} != expected:
        raise ValueError("Unexpected input file set")
    facts = [
        check_bytes(directory / "Cedar House Brief.txt", PAIR_BYTES),
        check_bytes(directory / "Cedar House Site Notes.txt", CONTROL_BYTES),
    ]
    if duplicate_bytes is not None:
        facts.append(check_bytes(directory / "Cedar House Brief - emailed.txt", duplicate_bytes))
    return facts


def verify_plan(root):
    root = Path(os.path.abspath(root))
    plan = plan_data(root)
    facts = inputs(root, PAIR_BYTES)
    for key, name in (("candidate_identity", "Cedar House Brief - emailed.txt"), ("reference_identity", "Cedar House Brief.txt")):
        identity = read(root / "Project Documents" / name)[1]
        if list(identity) != plan["candidates"][0][key]:
            raise ValueError("Selected plan identity no longer matches its actual open file")
    if any(safe(root / "Review Copies").iterdir()):
        raise ValueError("Quarantine must still be empty before execution")
    return {
        "candidate_count": 1,
        "plan": plan,
        "files": facts,
        "receipt_path": str(root / "Review Copies" / plan["plan_id"] / "receipt.json"),
    }


def verify_receipt(root, status):
    if status not in ("quarantined", "restore_collision", "restored"):
        raise ValueError("Not a terminal expected workflow status")
    root = Path(os.path.abspath(root))
    plan = plan_data(root)
    quarantine = safe(root / "Review Copies")
    if {p.name for p in quarantine.iterdir()} != {plan["plan_id"]}:
        raise ValueError("Unexpected quarantine run set")
    run = safe(quarantine / plan["plan_id"])
    receipt_path = run / "receipt.json"
    receipt = load_json(receipt_path)
    if type(receipt.get("version")) is not int or receipt["version"] != 1 or receipt.get("plan") != plan:
        raise ValueError("Receipt does not bind the exact saved selected plan")
    items = receipt.get("items")
    if not isinstance(items, list) or len(items) != 1:
        raise ValueError("Receipt must contain exactly the selected duplicate")
    item = items[0]
    duplicate = root / "Project Documents/Cedar House Brief - emailed.txt"
    item_id = str(uuid5(UUID(plan["plan_id"]), os.path.normcase(os.path.abspath(duplicate))))
    if (
        item.get("item_id") != item_id
        or item.get("original_path") != str(duplicate)
        or item.get("name") != duplicate.name
        or item.get("status") != status
        or type(item.get("size")) is not int
        or item["size"] != len(PAIR_BYTES)
        or item.get("sha256") != hashlib.sha256(PAIR_BYTES).hexdigest()
    ):
        raise ValueError("Receipt item identity/status/bytes do not match the actual fixture")
    if status == "restore_collision" and item.get("detail") != "Original path is occupied; existing file was kept.":
        raise ValueError("Receipt does not disclose the occupied destination")
    payload = run / "payload" / item_id / duplicate.name
    files = inputs(root, {"quarantined": None, "restore_collision": COLLISION_BYTES, "restored": PAIR_BYTES}[status])
    if list(read(root / "Project Documents/Cedar House Brief.txt")[1]) != plan["candidates"][0]["reference_identity"]:
        raise ValueError("The retained original no longer has its reviewed filesystem identity")
    if load_json(run / "plan.json") != plan:
        raise ValueError("Immutable quarantine plan differs from the reviewed saved plan")
    expected_files = {receipt_path, run / "plan.json", run / ".lock"}
    if status != "restored":
        files.append(check_bytes(payload, PAIR_BYTES))
        expected_files.add(payload)
    actual_files = set()
    for path in run.rglob("*"):
        safe(path)
        if path.is_file():
            actual_files.add(path)
    if actual_files != expected_files:
        raise ValueError("Missing or unexpected durable quarantine file")
    if status == "restored" and os.path.lexists(payload):
        raise ValueError("Restored payload still exists")
    return {
        "status": status,
        "receipt_path": str(receipt_path),
        "receipt": receipt,
        "receipt_sha256": hashlib.sha256(read(receipt_path)[0]).hexdigest(),
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "plan", "quarantined", "restore_collision", "restored"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    value = (
        prepare(args.root)
        if args.command == "prepare"
        else (verify_plan(args.root) if args.command == "plan" else verify_receipt(args.root, args.command))
    )
    print(json.dumps(value, ensure_ascii=True))


if __name__ == "__main__":
    main()
