"""Record real filesystem evidence for qualification failures in temporary files."""

import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.cleanup_plan import CleanupCandidate, CleanupPlan, EvidenceKind, files_equal, validate_candidate  # noqa: E402
from core import quarantine  # noqa: E402


def stat_values(info):
    return {
        name: getattr(info, name, None)
        for name in (
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_birthtime_ns",
            "st_dev",
            "st_ino",
            "st_file_attributes",
        )
    }


payload = {"python": sys.version, "cases": []}
with tempfile.TemporaryDirectory(prefix="twinquay-qualification-") as temporary:
    root = Path(temporary)
    for index, name in enumerate(("duplicate.bin", "duplicate-é.bin")):
        left, right = root / name, root / f"reference-{index}.bin"
        left.write_bytes(b"same contents\r\n" * 1000)
        right.write_bytes(left.read_bytes())
        candidate = CleanupCandidate.capture(left, right, EvidenceKind.EXACT_CONTENT)
        row = {"name": name, "lstat": stat_values(left.lstat())}
        with left.open("rb") as stream:
            row["fstat_before"] = stat_values(os.fstat(stream.fileno()))
            stream.read()
            row["fstat_after"] = stat_values(os.fstat(stream.fileno()))
        row["path_after"] = stat_values(left.lstat())
        row["files_equal"] = files_equal(left, right)
        row["eligibility"] = vars(validate_candidate(candidate))
        try:
            row["digest"] = quarantine.digest(left)
        except Exception as error:
            row["digest_error"] = repr(error)
        try:
            receipt = quarantine.execute_plan(CleanupPlan.create([candidate]), root / "quarantine")
            row["receipt_items"] = [vars(item) for item in receipt.items]
            row["remaining_files"] = []
            for staged in receipt.receipt_path.parent.glob("payload/**/*"):
                if not staged.is_file():
                    continue
                snapshot = {"name": staged.name, "lstat": stat_values(staged.lstat())}
                with staged.open("rb") as stream:
                    snapshot["fstat_before"] = stat_values(os.fstat(stream.fileno()))
                    stream.read()
                    snapshot["fstat_after"] = stat_values(os.fstat(stream.fileno()))
                    snapshot["path_while_open"] = stat_values(staged.lstat())
                snapshot["path_after_close"] = stat_values(staged.lstat())
                try:
                    snapshot["digest"] = quarantine.digest(staged)
                except Exception as error:
                    snapshot["digest_error"] = repr(error)
                row["remaining_files"].append(snapshot)
        except Exception as error:
            row["quarantine_error"] = repr(error)
        payload["cases"].append(row)
output = Path("build-evidence/windows-filesystem-probe.json")
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=True))
