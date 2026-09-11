# TwinQuay disposable MSIX qualification handoff

Implemented against reviewed source `e7a7ec85881b0c3e11c8505890a39e55b252da27` on `codex/twinquay`. This extends the approved native PyInstaller/Qt6 build; it does not alter scanning, quarantine/restore, preferences, the Qt6 migration, original artwork, or `tools/python-windows-lock.txt`. The exact commit of each native run is captured by Git, the inventory, startup receipt, package record and installation evidence. The coordinator owns public snapshots, Windows execution, release status and Store submission.

I downloaded and inspected the real metadata from prior Windows run `34578929213`, public snapshot `b05ca832e111adca548013a20d6abeadcb0831bf`. Its 417 staged files confirm every required `_internal/python312.dll`, PyQt6 binding, Qt6 DLL and `qwindows.dll` path used below. Its actual native startup receipt records exact title `TwinQuay` and executable SHA-256 `6CEB033BE5E8A944622CB4B9A4C7777723D3700B2C3E39A162F422EAB51050D1`. Download: `/tmp/twinquay-msix-prior-run/TwinQuay-windows-qualification`. That historical run predates these helpers and is not MSIX evidence.

## Boundary and provenance

`package.py` still produces its real `dist/TwinQuay` onedir output. `tools/package_inventory.py` now records a versioned whole-tree inventory, actual source revision, source notice/artwork/lock hashes, exact Python/PyQt6/Qt6 runtime paths, and unresolved dependency-notice names. All original image files and app GPL/third-party notices must match source bytes. Python, PyInstaller, PyQt6, Qt6 and SIP notice-inventory entries are required; every declared notice file must exist and be nonempty. Entries whose texts are unavailable must explicitly remain `required`. These entries are release gates, not license clearance.

The source-backed title check parses the real `qt/app.py` `NAME` assignment. A separate test verifies the real `More Options` QPushButton in `qt/directories_dialog.py`. The native startup receipt now matches exactly `TwinQuay` and binds its executable, source commit and the entire inventory's raw SHA-256. Packaging rejects changed/extra/missing stage files, changed runtime or notices, changed original assets/lock/source metadata, a failed or mismatched startup receipt, and a coherently substituted source revision.

The record labels the embedded PyInstaller bootloader and locally compiled `.pyd` modules as **build outputs, not wheel-identical files**. Installed distribution versions remain in `build-evidence/python-freeze.txt`; acquisition hashes remain in the unchanged Python lock, which is itself source-bound. Existing pins include PyInstaller 6.22.2, PyQt6 6.11.0, Qt6 6.11.2 and SIP 13.12.0. The existing build requires Python 3.12 x64; the workflow's `3.12` setup selector remains unchanged. This is an inventory/provenance record, not a claim of reproducible wheel-to-binary identity or corresponding-source completion.

## Package and installation flow

`tools/msix/qualify-msix.ps1` runs after the existing native feature tests, Qt smoke, PyInstaller build and real staged startup. The Python boundary tests also run before the native build. It uses **Windows SDK 10.0.26100.0 x64** MakeAppx and its exact sibling SignTool; records their actual hashes and rechecks tool bytes. No `/nv` or overwrite option is used. The fixed disposable identity is:

- Package `Trieflow.TwinQuay.Qualification`, publisher `CN=TwinQuay-CI-Qualification`.
- Version `1.0.0.0`, x64, application `TwinQuay`, executable `TwinQuay.exe`, `Windows.FullTrustApplication`.
- Exactly one `runFullTrust` capability; no protocols, associations or other extensions.

The original source icon is deterministically resized into the three manifest assets. A new build-owned stage/output is required. Independent ZIP/OPC verification decodes names exactly once, rejects malformed or escaped separators/traversal, aliases, duplicate/extra/missing entries, symlink/special entries and changed hashes, then checks the manifest semantics independently of recorded hashes. SDK-unpacked payload must match the same complete map. Before install, the current source/stage/startup/artwork boundary is reconstructed and compared with the record and actual unsigned package again. The whole installed payload is also checked, permitting only the standard package/signature metadata outside the source-bound payload.

The installer refuses preexisting matching registrations. It creates a nonexportable ephemeral key and imports only its public certificate into TrustedPeople, signs a separate copy and verifies the signature. The unsigned input is rechecked after signing and after cleanup. No private-key export or production signing identity is used.

Registration ownership is established only after this invocation's `Add-AppxPackage` succeeds and exactly one expected x64 registration is observed. Cleanup removes only that captured exact `PackageFullName`. A registration that races in before a failed Add, an ambiguous registration, a wrong architecture, or an observation failure is retained and reported. Matching name/publisher/version alone is never cleanup ownership.

The Windows broker activates the exact AUMID. The helper retains the returned live Process/SafeHandle; validates installed executable path/hash and actual `GetPackageFullName`; and only then establishes process cleanup ownership. It never reacquires a PID in cleanup. Every observed native module must be hash-matching package content or a hashed Windows file. Python, the PyQt6 binding, Qt6 Core/Gui/Widgets and the Windows platform plugin must be loaded from their exact packaged paths. Reparse ancestors and modules outside package/Windows fail. The real `TwinQuay` window must survive at least three seconds, expose its visible enabled `More Options` button, and produce a varied, owned-foreground screenshot wholly on the visible desktop. Unexpected visible error/modal windows fail. A title alone is not accepted.

Normal window close must produce an observed zero exit. Timeout, nonzero exit and observation error are separate fields; cleanup's exit observation is retained separately. Primary failure, cleanup failures and final unsigned-hash/evidence-write failures are preserved. Process handles are disposed after observation/cleanup. Exact owned package removal and both certificate-store removals are checked; personal certificate removal requests deletion of its ephemeral private key with the Windows certificate provider's `-DeleteKey`. All workflow, cleanup/restore, scanning, upgrade, WACK and public-release acceptance flags remain false regardless of package startup success.

The reused packaging/orchestration foundation is MIT PixelQuay (including the `b7672df8` native-stdout isolation fix), with the CutQuay exact-registration ownership correction and FileQuay `39f6fadb` retained-handle/exit pattern. MIT notices are retained in `tools/msix/PIPELINE-MIT.txt` and `RETICLEQUAY-MIT.txt`. .NET/GTK/Electron application assumptions were removed: the app runtime is its existing PyInstaller/Python/Qt6 payload. PowerShell/.NET only implements the external Windows qualification observer.

## Local verification, 2026-09-11

No GUI/browser was opened on the locked Mac. Local interpreter: `env-qt6/bin/python` (**Python 3.12.7, Qt 6.11.0, PyQt 6.11.0**); boundary fixtures also passed with system Python 3.10. The unchanged Windows dependency lock instead supplies Qt 6.11.2. PowerShell tests executed with actual **PowerShell 7.6.6**; embedded broker/PInvoke types compiled there. Black **24.8.0** formatted the Python helpers; the app's dependency lock was not changed to install tools.

- Initial **RED:** 15 package-boundary cases failed before the helper existed (`/tmp/twinquay-msix-red.log`). Follow-up regression rejected the previously accepted removal of the Qt6 dependency notice entry despite regenerated inventory (`/tmp/twinquay-msix-notice-red.log`). Source/record preflight and window-policy tests also failed on their absent implementations before being added.
- Actual process cleanup **RED:** the real cleanup closure killed a live, deliberately unverified broker-process fixture. After the explicit identity-ownership guard, that process survives and only a verified owned process is stopped. `/tmp/twinquay-msix-process-ownership-red.log` and `...-green.log`.
- Cleanup-exit retention **RED:** the real final evidence lacked `cleanup_process_exit`; the passing version now preserves the observed owned process ID/exit while leaving unowned cleanup evidence empty. `/tmp/twinquay-msix-cleanup-exit-red.log`.
- Final Python **GREEN: 20 tests pass**, using real temporary files, original PNGs, ZIP/XML parsing, source metadata, notice inventories and a controlled SDK-command adapter. They cover complete stage/record binding, native prerequisites, original asset/notice changes, explicit unresolved notices, source/receipt mismatches, links/native junctions, case/OPC aliases, traversal, extras/omissions, semantic manifest changes, exact SDK command flags/tool mutation, installed extras and a rehashed record substitution. The SDK adapter is a fixture, not actual MakeAppx execution.
- PowerShell **GREEN:** 6 orchestration scenarios (including native stdout isolation), 5 actual outer reporting/file-hash scenarios, 9 actual registration-closure scenarios (including failed-Add races and normal uninstall), 3 process wait/exit/observation cases plus 2 real process ownership/cleanup cases, and one complete window-policy fixture plus 8 negative variants. Appx cmdlets and actual UI are replaced only in these explicitly local policy fixtures; live process tests run real PowerShell children.
- Existing core suite: **566 passed, 1 skipped** of 567 on macOS. The unchanged skip is `core.tests.cleanup_plan_test.test_unique_extra_file_metadata_is_not_treated_as_duplicate`, reason `No extended metadata API`. Existing Qt6 suite: **14 passed**, using the existing headless Qt fixtures. No native Windows claim follows from either result.
- All changed/new PowerShell files parsed with the actual 7.6.6 parser; workflow YAML parsed; Python byte-compilation, Black check and Git whitespace checks passed.

Commands:

```sh
python3 tools/msix/test_msix_qualification.py -v
env-qt6/bin/python -m pytest core hscommon -q
env-qt6/bin/python -m pytest qt/tests -q
# With the available pwsh 7.6.6 executable:
pwsh -NoProfile -File tools/msix/test_qualify_msix_install.ps1
pwsh -NoProfile -File tools/msix/test_msix_evidence.ps1
pwsh -NoProfile -File tools/msix/test_registration_ownership.ps1
pwsh -NoProfile -File tools/msix/test_process_observation.ps1
pwsh -NoProfile -File tools/msix/test_window_evidence.ps1
```

Local logs and JUnit receipts are under `/tmp/twinquay-msix-*.log` and `/tmp/twinquay-msix-{core,qt}.xml`; no generated test copies were committed.

## Coordinator execution and remaining gates

On a fresh disposable Windows runner, the workflow executes:

```powershell
./tools/build-windows.ps1
./tools/test-packaged-startup.ps1
./tools/msix/qualify-msix.ps1
```

`CI=true`, exact `GITHUB_SHA`, Python 3.12 x64, PowerShell 7, SDK 10.0.26100.0 and the existing native compiler are required. The package step has a 10-minute workflow timeout. No factory reset, settings injection, package-name cleanup sweep, dependency override or mutable registry fetch was added.

Only metadata/log/XML/PNG files are uploaded: whole-stage inventory, startup receipt, package record, installed payload/module/window/exit/ownership evidence, screenshot and preserved failures. The package/signing work remains under a newly owned runner temporary directory; no MSIX/native binary, certificate, key or personal profile is uploaded.

**Not executed locally:** actual SDK semantic validation/unpack, Windows certificate trust/signature, package installation, broker activation, installed Python/Qt6 module observation, genuine UIA screenshot, normal installed close, exact uninstall/certificate cleanup, or independent source acceptance. The coordinator must dispatch and inspect those results before claiming temporary installation qualification. Duplicate scanning, quarantine/restore, upgrade, accessibility/DPI, WACK, native source/license delivery, production Store identity/signing, Store submission and release status remain separate gates.
