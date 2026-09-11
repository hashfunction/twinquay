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

## Native modal window discovery repair

Windows run `34640354182` (source `80ac39ba16f9e9fbd58c543882a937c84270fbb8`,
public snapshot `c35d6ef0a48f59239f9ce76b97b937045f0ee881`) reached installed
startup, then failed before scanning. Its retained `failure-window-0.json`
contains the exact source title **Select a folder to add to the scanning list**
as a visible owned Window below the TwinQuay UIA root. The helper searched only
desktop children and timed out; failure capture then targeted the owner while
its modal dialog was foreground. The title was not missing or renamed.

Discovery now searches each owned UIA root's bounded subtree. Each returned
Window must have a nonzero native HWND, the same observed native PID, visibility,
and `GetAncestor(GA_ROOT)` equal to itself. Handleless Qt child widgets and foreign
windows are excluded; repeated representations of one HWND are deduplicated.
Two different HWNDs with the same exact expected title still fail as ambiguous.
Keyboard input additionally rechecks native HWND ownership and still requires
that exact HWND and PID in the foreground. No title prefix or blank-title
fallback was introduced.

The same native evidence exposes **Select Folder** as a UIA Pane. The three
source-defined folder/save dialogs therefore use a narrow native-button path:
unique exact UIA name, exact source dialog title and native `#32770` class,
owned visible/enabled HWNDs, actual `Button` class, IDOK=1, exact caption and
native child/root relationship. `WM_NEXTDLGCTL` requests focus; `GetGUIThreadInfo`
must observe that exact button immediately before real Space input. A generic
Pane, foreign/disabled control or changed focus cannot pass. The existing Qt
button path is unchanged. Failure capture now records native window metadata
and continues to later owned windows after an owner screenshot refusal, retaining
every diagnostic failure without weakening foreground or image bounds.

`test_workflow_windows.ps1` reproduces the original timeout locally by replaying
the actual owner/modal topology through production traversal. The repair passes
that replay, exact-title/foreign/handle/ambiguity cases and nine native-button
identity negatives. Only unavailable Windows APIs are adapted on macOS.
On Windows the same required test executes the actual
`DirectoriesDialog.addFolderTriggered` and `CleanupPlanDialog.save_plan` methods
in a separate real Qt/IFileDialog host, selects an owned metacharacter path,
saves actual JSON and requires observed normal exit. The fixture uses no package
identity and is not installed-app acceptance; the existing installed workflow
must still run afterward with all package/module/source/cleanup gates intact.
The fixture's JSON/stdout/stderr evidence uses the existing metadata-only globs.

Local verification: 615 Python/core/Qt tests passed, one existing platform
metadata skip; all nine PowerShell fixture programs passed; new Python compiled
and Black check passed; changed PowerShell files parsed and real C# interop
compiled. The real Windows native dialog/input branch remains pending execution.

Primary API references:
- https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-tree-overview
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getancestor
- https://learn.microsoft.com/en-us/windows/win32/dlgbox/wm-nextdlgctl

### Transient scan progress in run34642776050

The real Windows Qt/IFileDialog source fixture passed and the installed app
selected the exact owned input folder. During Scan, native HWNDs393552 and262676
had the same exact TwinQuay title and PID7412; the latter exposed a progress bar
and Cancel. Immediate ambiguity rejection stopped the observer before results.
The existing bounded wait now waits for one unique observed match; it never
selects either ambiguous window. Persistent ambiguity still fails at the deadline,
while owned error windows and observation failures remain immediate failures.
The independent wait probe reproduced the prior failure and verified 2→0→1,
persistent ambiguity, case/prefix mismatch and later error/observation failures.
No product code or destructive workflow operation changed. Native qualification
of this later observer is required. Secondary failure-only screenshot diagnostics
from the old progress window remain recorded; they are not success evidence.
