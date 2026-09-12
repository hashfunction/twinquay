# TwinQuay disposable MSIX qualification handoff

Historical qualification record. Current DupliSift naming, compatibility and screenshot fixtures are documented in [the rename review](duplisift-rename-review.md). Old run titles, package paths and source commits below remain unchanged.

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

## Independent review repair: source-copied notices

Independent review reproduced a replacement of the staged Hardcoded Software BSD notice that could be hidden by fresh inventory/startup/package records. The collector copies this file directly from `hscommon/LICENSE`; it also creates a second copy of `THIRD-PARTY-NOTICES.txt` under `notices/`. Both copies are now compared byte-for-byte against their original source files before fresh receipts can be produced, and the BSD original is included in the source input hashes. A regression seeded from the actual BSD source text failed for both replaced notice copies before the fix; all 21 package-boundary tests now pass. No product behavior, runtime, dependency lock or notice text changed. The earlier Windows run at source730a8b1 predates this repair and cannot qualify the repaired source.

## Native module policy correction

Actual Windows run34604065415 built, packed, unpacked, signed and installed the package, then broker-started TwinQuay with the expected title. It failed at `C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.3-0\MpOav.dll`, outside the prior SystemRoot-only OS rule. Exact owned cleanup still passed. Microsoft documents the Defender platform location at https://learn.microsoft.com/en-us/defender-endpoint/collect-diagnostic-data and Defender AMSI integration at https://learn.microsoft.com/en-us/defender-endpoint/amsi-on-mdav . The revised observer accepts only the observed `MpOav.dll`, directly beneath a numeric platform-version directory in the Windows CommonApplicationData Defender platform root, with non-reparse ancestors, regular-file checks, a valid Authenticode signature whose signer CN and organization identify Microsoft, and stable SHA256 across signature verification. Module evidence records its distinct OS security-provider origin, certificate identity and digest. No Defender settings or product binaries change.

The new helper was absent in RED; GREEN covers one explicitly mocked valid-signature metadata fixture and 13 signature/path/hash-change/link negatives. PowerShell parsing, six orchestration and five reporting scenarios pass. Signature trust verification is still an actual Windows run requirement; local mocked signatures are not authentic Windows evidence.

Independent review then reproduced a signer-name parsing defect: the displayed X500 subject can embed Microsoft CN/O strings inside a quoted OU. The original text regex accepted that fixture. The revised check reads actual `Certificate.SubjectName` DER through .NET `EnumerateRelativeDistinguishedNames`, rejects multi-valued RDNs, and requires exactly one CN (OID2.5.4.3) and one O (OID2.5.4.10) with exact Microsoft values. Quoted OU spoof and duplicate CN/O regressions are now rejected; one positive and 16 negative metadata/path cases pass. API reference: https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.x509certificates.x500distinguishedname.enumeraterelativedistinguishednames . Native Authenticode trust is still required and cannot be inferred from the local metadata fixtures.

Run34605783622 at131a583 retained the actual platform certificate: Authenticode `Valid`, parsed CN `Microsoft Windows`, O `Microsoft Corporation`, issuer `Windows Production PCA 2023`, thumbprint `26629E2872A1E61E669CC62CF9CF2DAFF05473B3`. This is a third exact Microsoft CN used by the observed Defender module, and is now recognized alongside the existing exact names. Its real parsed identity fixture failed before this addition. All three positive identity fixtures and 16 rejection cases now pass. Path/module restrictions, parsed DER identity, valid chain requirement and stable digest checks remain in force. This run did not yet qualify installed module/UI/close behavior.

## Temporary-directory ownership correction

During DayQuay adaptation, an actual preparation/cleanup closure probe reproduced
an ownership edge in baseline `1ee1e1849ad2aad030717b7ba56254197436ea4e`: the helper
stored the future signing directory in cleanup state before `New-Item` succeeded.
If creation failed because another owner occupied the candidate, cleanup could
remove that unowned directory. The new `test_temporary_ownership.ps1` supplies a
real colliding directory and preserved marker, runs the actual preparation and
cleanup closures, and was RED with `Unowned colliding temporary directory was
deleted` before the correction.

Preparation now uses a local candidate and assigns `$state.temporary` only after
exclusive directory creation succeeds. The same regression is GREEN and is part
of the normal `qualify-msix.ps1` fixture list. This is the only behavior change;
package identity, signing, module/UI/exit observation, native dependencies,
registration ownership and public release gates are preserved.

Validation: all 21 Python packaging tests, all seven PowerShell fixture suites,
nine PowerShell script parses, embedded native C# compilation and diff checks
pass. PowerShell 7.6.6/.NET 10.0.12 ran the actual closure/process tests locally.
The coordinator reported Windows run `34607114421` successful before this repair;
that run does not qualify this modified source. A fresh exact-source native run
and independent review remain required. No GUI, account, publish or push action
was performed by this repair.

## Inherited record and observation repairs

Independent review reproduced two missing failure checks. Seven real package
record variants (missing/empty/zero/string/float/bool/extra-field unpack evidence)
were RED before requiring the exact integer unpack count from the source-bound
payload. A real Add/cleanup closure with successful Add and no visible registration
was RED before reporting unresolved cleanup uncertainty without claiming ownership
or deleting any package. Both regressions now pass: 22 package tests and ten
registration flows. The previous successful Windows run remains historical;
this source revision needs a fresh qualification.
