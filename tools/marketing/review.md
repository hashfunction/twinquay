# DupliSift capture-only implementation review

Base: local `071f31798e362b5ea5c5176f0e7270d728283bd4`, whose public snapshot `73f3842a2cc81aa3c69a5873a262517eae35b6f4` passed Windows run `34683417158`.

Scope is new `tools/marketing/*` and `.github/workflows/marketing-screenshots.yml` only. Existing product, qualification, source/notices, version, assigned identity and legacy data paths are untouched. No push, publication, parent status, website or Store edits were performed.

The package/run/readiness bindings are documented in README. Input verification on the retained actual artifacts passed against every original unsigned payload entry (600), both full installed lifecycles, all 79 uploaded evidence files and the three source-publication records. The original six unuploaded profile entries are explicitly identified; no assertion was manufactured for missing bytes. A real temporary Git checkout with `core.autocrlf=true` reproduced the original Windows source helper hashes and passed the actual evidence validator; the default LF checkout correctly failed that equality. Retained local checkout: `/private/tmp/duplisift-capture-qualified-crlf`. Original artifacts: `/private/tmp/duplisift-34683417158-review`.

Focused verification completed locally:

- `env-qt6/bin/python -m unittest discover -s tools/marketing -p 'test_*.py' -v`: 7 tests passed, including changed run/readiness/identity and production ZIP download/extraction refusals.
- `pwsh -NoProfile -File tools/marketing/test_capture_helpers.ps1`: native RECT ABI, 1800×900 placement, owned-frame before/after checks, foreign/changed/clipped/invalid geometry refusals, failed-Add and unproven-process cleanup guards passed.
- `pwsh -NoProfile -File tools/marketing/test_display_modes.ps1`: native DEVMODE/DISPLAY_DEVICE layouts, enumerated selection, test-before-apply, temporary flags, retained mode restoration and partial failure passed.
- `TMPDIR=/private/tmp pwsh -NoProfile -File tools/marketing/test_capture_adapter.ps1 -Python <env-qt6/bin/python>`: the actual original workflow constructs its operations and runs its real Prepare/oracle closure with the short owned root. Injected native-stage failure retains the original error, restores the signing directory and clears the capture interpreter binding. Original surface failure prevents an additional screenshot, conflict recording stays unchanged, restored-row substitutions fail, and exclusive ownership-marker refusals pass.
- `TMPDIR=/private/tmp env-qt6/bin/python tools/marketing/verify_restored_view.py`: actual Qt 6.11.2 UI plus real domain scan-plan/quarantine/collision/restore receipts; reopening the original dialog shows one five-column row, exact original path, restored status and disabled checkbox. Restored file evidence is unchanged. This is a real Qt/domain replay, not Windows UIA or screenshot acceptance.
- `TMPDIR=/private/tmp env-qt6/bin/python tools/msix/test_workflow_files.py -v`: all 10 unchanged file/receipt tests passed.
- Unchanged PowerShell `test_workflow_helpers.ps1`, `test_workflow_observation.ps1`, `test_workflow_windows.ps1`: passed, preserving existing owner/input/modal/chooser/conflict/orchestration boundaries.
- Every new PowerShell file parsed; Python files compiled; `git diff --check` passed.

PowerShell used `/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`. Python used this source's existing `env-qt6/bin/python`. No new dependency download was needed. The dispatch workflow checks its platform-neutral capture fixtures before downloading the exact artifacts; Windows itself exercises the installed UIA and original workflow.

The original package is already qualified and is unchanged. No new native capture has run, and no marketing screenshot has been manufactured locally. Fresh Windows execution must prove actual display/window placement, the visible restored receipt columns, three authentic PNGs, normal exit and complete cleanup. If native placement cannot expose the source UI at the required size, capture fails with its current evidence instead of changing product behavior or weakening the original workflow.
