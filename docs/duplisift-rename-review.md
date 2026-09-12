# DupliSift 1.0.1 rename and native screenshot fixture

Base source: `a5a7c7476da1939bdcd3094fa0754897361a5e39`. The coordinator provided the authenticated Store-reserved name **DupliSift** and canonical `https://duplisift.trieflow.com`; the implementation follows the portfolio rename plan. This is a source candidate awaiting independent review and a fresh Windows run. No package, site or source publication is claimed.

## Closure review before renaming

The preceding candidate was reviewed against its retained original Qt PDF build/configuration/SBOM records, exact module hashes, generated attribution pages, Microsoft Runtime EULA/transcript and downstream distribution reference. Its six staging/checkout tests and three original-document preparation tests pass. The package still carries all 206 supplemental source notice files and 15 original-build/runtime notice files. The archive list is still the 71 verified source assets, with final application source/publication flags false.

After the rename, **243 original source/archive/provenance records and notice payload files** compare byte-for-byte with the base. This includes the acquisition manifest, source-release asset plan, 114-native-file provenance, Windows system baseline, original Qt PDF build evidence and all original build-record files. In the supplemental notice mapping and its index, only the current-product scope sentence changed; every archive reference, selected member, size and hash is unchanged. The sentence now points to the separately completed PDF/Microsoft notice set instead of saying those materials are still missing. No immutable dependency source asset or original attribution was renamed.

The final app source snapshot remains unassigned until the coordinator publishes the exact renamed source. The source/recombine route still uses external Qt/PyQt libraries and the normal unpackaged executable, with no runtime hash/signature allowlist. Modified-library Windows execution remains unobserved. The current release also still requires public source verification, fresh package qualification and the applicable downstream license presentation.

## Product and compatibility

- UI titles, Help/About, notices, package metadata and Windows version resources identify **DupliSift 1.0.1**; MSIX is **1.0.1.0**. Current links use the new product/privacy/support/source URLs. These links are the coordinator's canonical targets, not a claim that this task deployed them.
- The source recipe is `DupliSift.spec`; the directory/executable is `dist/DupliSift/DupliSift.exe`. Store upload staging names `DupliSift_1.0.1.0_x64.msix`; disposable staging names `DupliSift.Qualification_1.0.1.0_x64.msix`. Workflow artifacts are `DupliSift-windows-qualification`. NSIS display/output and source-archive names use the new brand. The tracked-spec ignore exception was updated so a source snapshot contains the renamed recipe.
- Store Identity Name remains **1659hashfunction.TwinQuay**, Publisher remains **CN=B6A2631A-FD32-45CC-AE12-82466975F528**, PublisherDisplayName remains **hashfunction**, and ApplicationId remains **TwinQuay**. The disposable identity and publisher remain fixed too. Both installed modes still run sequentially and retain metadata only; no binary export gate was added or relaxed.
- Windows data remains `%LOCALAPPDATA%/TwinQuay`; portable data remains `data/TwinQuay`. New portable setups use `DupliSift.ini`. An existing `TwinQuay.ini` takes precedence when both files exist, preserving the previous profile rather than silently switching settings. Four actual QSettings-file tests cover Windows, new portable, legacy portable and dual-file precedence.
- New result/directory-list saves use `.duplisift`/`.duplisiftdirs`. Existing `.twinquay`, `.twinquaydirs` and upstream dupeGuru files remain readable, including old command-line result opens. Explicit legacy suffixes are preserved on save. Core result/plan/receipt formats and user data migration behavior are unchanged.
- All **16 original artwork files** are byte-identical under `images/duplisift`; current help moved to `help/duplisift`. No screenshot pixels or upstream credits were edited. Historical qualification documents retain old run titles/paths and now point to this current review. Internal helper names and historical evidence still use TwinQuay where appropriate.

## Real screenshot fixture

The existing installed consumer workflow creates original fictional **Cedar House** renovation documents inside its exclusively owned temporary directory:

- `Project Documents/Cedar House Brief.txt`: the project brief to retain.
- `Project Documents/Cedar House Brief - emailed.txt`: the exact same original brief, selected for review/quarantine.
- `Project Documents/Cedar House Site Notes.txt`: distinct original notes, required to survive unchanged.

The user-selected quarantine directory is `Review Copies`; the saved plan is `Cedar House - Cleanup Plan.json`. The documents include an original room survey checklist and exceed the fresh profile's unchanged 10 KB minimum. A regression executes the actual production Contents scanner with its default settings and requires exactly the intended pair; its initial short-document version correctly failed this check. The documents are newly authored ASCII/UTF-8 text, copyright 2026 Trieflow LLC, and contain no real customer information. Their original content and provenance are recorded by `workflow_files.py`; the native receipt includes actual file hashes/identities and the sample provenance statement.

The live application still performs the Contents scan, exact original-row selection, cleanup review, chosen folder, fresh byte verification, quarantine, occupied-destination refusal, restoration and normal close. The independent oracle still requires exactly one duplicate, preserved original filesystem identity and unique-control bytes, exact selected plan/receipt/hash binding, collision preservation, restored bytes and removed payload. The ordinary owned cleanup gates are unchanged. Only brand, executable/version and sample path/content literals changed in the native workflow; no input ownership or success predicate was relaxed.

The existing nine capture points still photograph the actual retained installed process, from folder selection through results, review, quarantine, conflict and restoration. A fresh Windows run must produce these new captures. Local fixtures and old images are not replacement marketing evidence.

## Verification

Run from the source root using the existing `env-qt6` Python and the File source's PowerShell 7.6.6:

```sh
./env-qt6/bin/python build.py --clean
./env-qt6/bin/python -m pytest core hscommon -q
QT_QPA_PLATFORM=offscreen ./env-qt6/bin/python -m pytest qt/tests tools/msix/test_workflow_source_ui.py -q
./env-qt6/bin/python tools/smoke-qt.py
./env-qt6/bin/python tools/msix/test_msix_qualification.py -q
./env-qt6/bin/python tools/msix/test_workflow_files.py -q
PYTHONPATH=/private/tmp/twinquay-pefile-reader ./env-qt6/bin/python tools/test_collect_build_evidence.py -q
PYTHONPATH=/private/tmp/twinquay-pefile-reader ./env-qt6/bin/python tools/test_windows_system_libraries.py -q
./env-qt6/bin/python tools/test_native_notices.py -q
./env-qt6/bin/python distribution/corresponding-source/test_release_notices.py -q
./env-qt6/bin/python distribution/corresponding-source/test_materials.py -q
./env-qt6/bin/python distribution/corresponding-source/test_notices.py -q
```

Local build succeeds, compiling all three C extensions and regenerating localization/help with the renamed paths. Log: `/private/tmp/duplisift-local-build.log`. Qt 6.11.2 smoke imports all three rebuilt extensions and decodes every original asset.

Results: **566 core/utility passed, 1 skipped; 26 actual Qt/source UI passed; 24 package tests; 10 real file/receipt workflow tests; 10 collector + 8 system-library policy tests; 6 notice staging/checkout + 3 original-document + 6 material + 4 source-notice tests.** The new portable-file test first failed on the old implementation, then passed. The new sample-contract test catches renamed JSON keys, keeping the native `prepare.input`/`prepare.quarantine` interface stable.

PowerShell production fixtures pass for installation orchestration (6), final reporting (6 under each fixed identity), exact registration ownership (10), retained process/exit handling, window observation, Defender/text-input modules, fixed identity (26 changed-field cases plus cross-mode refusal), temporary-directory ownership, workflow sequencing/collision, incomplete UIA observation, owned recent-folder navigation, and native owner/modal topology. The native-metadata collector's hashing/signature serialization tests pass. The fixed-identity tests additionally reject old executable/version values and a renamed ApplicationId.

`test_workflow_sendkeys.ps1` cannot load Windows Forms on macOS; it remains required and unchanged in the Windows qualification workflow. The macOS native-dialog test replays production traversal and compiles interop; real Windows IFileDialog, activation, Authenticode, installed modules and the full renamed consumer screenshots remain unverified locally. PowerShell parsing and `git diff --check` pass.

No push, snapshot, public upload, website, parent status or Store submission was performed.
