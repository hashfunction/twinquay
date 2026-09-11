# Installed TwinQuay workflow qualification plan

Extend the reviewed temporary-MSIX qualifier at 6344e02a; retain its exact source,
package/broker identity, native-module confinement, live process ownership,
normal close and owned uninstall/certificate cleanup. Product code is unchanged.

Use one exclusive disposable fixture root outside uploaded evidence. Generate
one original/duplicate pair plus a different control file. In the actual installed
application, select Standard/Contents, use the real Add Folder chooser, scan,
select the original as reference, mark duplicates and open Review Cleanup Plan.
Save the actual selected plan through the UI and independently verify its single
candidate/reference/evidence/size against the generated files before execution.
Choose the private quarantine folder through the actual folder dialog, execute,
and capture the rendered plan/completion/receipt surfaces. Independently verify
original/control bytes, absent duplicate, exact payload and durable receipt.

Open Quarantine Receipts through its real shortcut, select the item and attempt
restore with an exclusively created DeleteOnClose collision file held open by
the qualifier. Verify the real restore_collision receipt, unchanged reference,
control, payload and occupied destination. Releasing that exact owned handle
removes the collision; never unlink a possibly replaced path. Restore through
the real UI again and verify both duplicates' exact original bytes, control,
restored receipt and absent payload. Close dialogs normally, then complete the
existing live-process/registration cleanup checks. Recheck package identity and
loaded-module confinement after interaction as well as before it.

UI operations use PID-confined AutomationElements and foreground-checked keyboard
input only; no hidden product modes, configuration injection, core cleanup API
calls or mocked UI results. Missing/ambiguous controls, timeouts, wrong paths,
changed bytes, non-terminal receipts and error surfaces fail closed. Preserve
bounded JSON/UIA trees/screenshots on failure; fixture bytes and private profiles
never enter public artifact globs. Local tests cover actual file/receipt validation,
selectors, key escaping, orchestration failure retention and live collision-handle
lifetime. They do not establish installed UI acceptance. Fresh Windows execution
and independent review are required before any workflow success claim.

## Implemented qualification contract

`tools/msix/qualify-workflow.ps1` runs inside the existing broker activation
operation. It uses the already verified, retained process handle; each UI action
rechecks the exact installed executable hash/path and `GetPackageFullName`.
Windows input is restricted to that process's exact foreground window. It never
starts a separate TwinQuay, calls a cleanup API, injects preferences or asks the
product to enter a testing mode. The product's own dialogs, shortcuts and jobs
perform every scan/quarantine/restore operation.

The only new files acted upon are generated beneath the qualifier's already owned
signed-copy temporary directory. `workflow_files.py` uses independent standard-
library readers to validate the plan, receipt, byte contents and original file
identity. Its production code imports no TwinQuay cleanup APIs. Tests use real
core receipts as oracle inputs; those tests are explicitly not UI qualification.
New filenames and evidence files use exclusive creation. A held `CreateNew` /
`DeleteOnClose` file supplies restore-conflict coverage and is released by its
original handle, including failure paths. A Windows reader with explicit
read/write/delete sharing can inspect that exact held collision. Primary workflow,
handle cleanup, diagnostic capture and exclusive reporting failures remain visible.

The generated duplicate pair is 32,811 bytes per file, above the actual default
10-KB small-file threshold. A distinct 18,154-byte control remains in the scan
folder. The saved plan must contain exactly `duplicate-copy.bin` referencing
`keep-original.bin`, `exact_content`, and the current full file identities. The
receipt must embed that exact selected plan, the expected UUID-derived item,
expected terminal status, exact digest/size and actual payload. The original's
reviewed identity must remain unchanged, including when replacement bytes happen
to match. Extra input/payload files, links/reparse paths, changed content and
premature receipt statuses fail. The post-restore results table is not presented
as a rescan; the application's actual completion text says to rescan after restore.

Qt-specific choices were checked against the exact runtime's primary source:

- [Qt 6.11.2 Windows UIA providers](https://github.com/qt/qtbase/blob/v6.11.2/src/plugins/platforms/windows/uiautomation/qwindowsuiamainprovider.cpp):
  QComboBox exposes ValuePattern; the helper requires its actual value `Contents`.
- [QAccessibleComboBox's value](https://github.com/qt/qtbase/blob/v6.11.2/src/widgets/accessible/complexwidgets.cpp):
  a non-editable combo returns its current text.
- [Qt table accessibility actions](https://github.com/qt/qtbase/blob/v6.11.2/src/widgets/accessible/itemviews.cpp):
  a cell's Toggle action selects/unselects it; it does not change CheckStateRole.
  The helper uses real Ctrl+Home then Space on the one-row receipt table and
  checks the resulting checkbox through UIA. A local actual QTableWidget/QTest
  test verifies that key sequence and the resulting restore selection.

After interaction the existing exact module-origin/hash policy runs again, then
`verify_record.py` rechecks source, package, stage and full installed payload.
Normal main-window close answers only the exact source-defined “Unsaved results”
question, if present, before requiring observed exit code zero. Existing exact
owned-package uninstall and certificate/process/temporary cleanup remain required.
Final `workflow_acceptance` cannot pass without the workflow, post-workflow module
checks, unchanged unsigned package and all prior installation/cleanup gates.

## Evidence and execution

The existing Windows workflow now runs the new tests and interaction through:

```powershell
./tools/build-windows.ps1
./tools/test-packaged-startup.ps1
./tools/msix/qualify-msix.ps1
```

It retains `build-evidence/msix-install/workflow/*.json` and `*.png`, including
per-stage trees/screenshots, independently read plan/receipts/file facts and final
workflow result. Existing installation JSON retains the workflow and separate
post-workflow module count; `loaded-modules-after-workflow.json` retains the full
module inventory. Failure capture is limited to eight visible owned windows,
1,500 nodes per tree and bounded on-screen screenshot rectangles. Fixture content,
encoded fixture bytes, executables, packages and signing material are excluded
from artifact globs. Every new JSON/PNG filename is exclusive.

Local verification commands (the existing `env-qt6` contains Qt 6.11.2/Python 3.12):

```sh
env-qt6/bin/python -m pytest core hscommon qt/tests tools/msix -q
pwsh -NoProfile -File tools/msix/test_workflow_helpers.ps1
```

Run all existing `tools/msix/test_*.ps1` fixtures as well. The actual Windows CI
uses its pinned `.venv/Scripts/python.exe`; helper tests use that same interpreter.
The Mac helper test uses the existing `env-qt6/bin/python` and does not open a GUI.

Local RED evidence includes the previous 6344 installer accepting a success with
no installed workflow (`test_msix_evidence.ps1` now rejects it), missing new oracle
and helper entry points, an initial unsupported Qt pattern selection caught by
source/real-widget checks, and fixture-content leakage rejected by a metadata-only
regression. Final local counts/logs are recorded in the parent handoff report.

This increment is an implementation awaiting independent review and fresh Windows
execution. Previous run 34613990545 qualified startup/installation only. It cannot
prove this new workflow. Windows UIA/native chooser behavior, actual held-file
sharing, rendered workflow evidence and normal exit must pass in the fresh run.
No new Windows success, full consumer acceptance, release, Store identity, upgrade,
WACK or licensing-clearance claim is made by the local tests.


## Bounded receipt completeness repair

Independent review reproduced a missing `.lock` being accepted by the initial
oracle. The terminal checks now require equality with the entire expected durable
file set: `receipt.json`, immutable `plan.json`, `.lock`, and the payload until
successful restore. The real-domain regression exercises quarantine, restore
collision and restored states. Each control passes, an extra file rejects, and
removing only `.lock` rejects; subsequent real restore operations recreate their
own lock normally. This changes only the external qualification oracle, with no
change to product locking or restore behavior. Fresh Windows execution remains
required after the source review.
