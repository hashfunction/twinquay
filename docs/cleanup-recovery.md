# Cleanup transaction and recovery contract

A plan is immutable and stores original/reference paths, scan evidence, size,
mtime, ctime and file identity. The scan mode is captured when results are
created, not taken from mutable preferences later. Loaded upstream result XML
has unknown evidence and cannot authorize cleanup. The former UI delete/move
entrypoints open plan preview. Legacy private upstream low-level operations
remain in source for existing unit coverage, but active DupliSift cleanup does
not call them. Copy/review/scan behavior remains available.

Plan rows are sorted by normalized path. Item IDs are deterministic UUIDs from
the plan ID and candidate path, so the displayed destination matches execution.
A plan cannot be executed twice into the same quarantine directory. A reference
selected elsewhere in the same plan refuses the entire cleanup plan.

`receipt.json` is written via exclusive temporary file, flush/fsync and atomic
replace before mutation and after every outcome. The receipt includes all items
before the first move. `plan.json` is immutable. An OS file lock prevents two
processes from acting on the same receipt; process death releases the lock.

Same-volume transfer uses a no-replace rename on Windows, or hardlink/unlink on
the POSIX development host. A private `.staging` path is fully checked again
before being published to the planned payload path. A changed moved file is
returned to its original path only if that path is still absent. Otherwise both
paths remain inspectable for manual recovery. Receipt errors never authorize
another item implicitly.

Cross-volume transfer copies to exclusive staging, flushes/fsyncs and verifies
current source/staging size and SHA-256 as well as fresh candidate/reference
byte equality. Source removal happens only after a durable `source_retained`
checkpoint. Windows then opens the source exclusively with read/delete access,
checks captured identity, repeats full pair comparison with the open handle,
and marks that exact checked handle for deletion using FileDispositionInfo.
A writer/lock/access error leaves source and verified payload in place.
These Win32 paths must be tested on Windows before release. The POSIX fallback
is for local development and does not claim adversarial concurrent-writer
safety; it revalidates before path unlink but lacks mandatory Windows sharing.

Restore verifies receipt schema and item/plan identity, rejects payload path
traversal, reads size/SHA-256, and publishes without replacement. Existing files,
including dangling links, cause `restore_collision`. If bytes change during a
same-volume restore, they are returned to quarantine when possible. Cross-volume
restore uses a unique staging file beside the original; its location is recorded
before writes. Quarantine stays intact if copying or verification fails.

Inspect these states without deleting anything:

| Status | Meaning/recovery |
| --- | --- |
| quarantined | Verified payload exists; original removed. Restore is available. |
| changed_since_plan / similarity_only / missing / read_only | Candidate refused; no intended cleanup. |
| cancelled | Item did not begin; keep the original. |
| moving / copying / restoring | Interrupted intent; inspect both recorded paths and `.staging`. Restore verifies before acting. |
| source_retained | Verified payload and original remain. Resolve the reported error manually. |
| recovery_required | A staged/payload file remains after failure. Inspect before retrying restore. |
| restore_collision | Original is occupied; DupliSift never overwrites it. |
| payload_changed / missing_payload / restore_failed | No successful verified restore. Keep all remaining files. |
| restored | The original path has been restored; rescan to refresh results. |

There is no unattended deletion, automatic receipt cleanup, or automatic
quarantine purge. Power-loss durability, junction/reparse races, OneDrive states,
Windows sharing locks, long paths, real cross-volume copies, NTFS metadata and
DPI/keyboard behavior remain native acceptance gates. Tests simulate failure
boundaries using real temporary payload files but do not substitute for those
OS-specific trials. Do not modify source/payload files concurrently with cleanup.
