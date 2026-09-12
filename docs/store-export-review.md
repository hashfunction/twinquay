# DupliSift unsigned Store export review

Base local source: `a21600ab705524c2ed62f6adc368de94d23adea3`. Successful published source: `7a88fceeec60a70e34e324a90deafe2101ed641e`, Windows run `34680779425`. Both original installed identities passed actual scan, review, quarantine, occupied-destination refusal, restore, normal zero close, uninstall and owned cleanup. The assigned Store unsigned package was 46,032,620 bytes, SHA-256 `d40956003877bff40ba60b2d84c797ea55e5057340159f197b690da79c8c7db5`; the existing job retained metadata only. This change does not retroactively retain that expired runner file or claim a new Windows success.

## Change

The Windows workflow explicitly requests `-ExportStore` and uploads only the two fixed paths in `DupliSift-Store-unsigned`, after the existing dual lifecycle step succeeds. Direct qualification without the switch preserves its no-export behavior. Child failures terminate the sequence, so either lifecycle or export failure prevents upload. The exact unsigned package paths are captured only after each successful installed qualification.

The exporter reuses complete `verify_record_inputs` source/stage/PNG/manifest/container/SDK-unpack validation for both modes, checks the current source/run/attempt in native startup and installed/workflow receipts, verifies matching standalone/embedded workflow facts, original fixture bytes through quarantine/conflict/restore, nine owned native screenshot hashes, loaded package module hashes, zero process exit, registration ownership and all cleanup results. Startup and installer/workflow reporting now retain CI run/attempt. Every existing UI, input, ownership, module and file oracle remains unchanged.

All 70 final native collector origins match the successful inventory. The ten Qt PDF/Microsoft DLL hashes still match the audited original configuration/redistribution evidence. All original notices, dependency locks, assigned identity `1659hashfunction.TwinQuay`, publisher, ApplicationId `TwinQuay`, executable/version and legacy data paths are preserved.

The root-supplied `native-source-publication.json` binds the exact 71 native source archives and historical plan at `native-sources-2026-09-12`, after anonymous full-byte verification of all 72 files. The exporter validates that record, re-downloads the small published plan, and anonymously downloads the exact current CI Git commit archive. Every tracked blob and executable/symlink mode must match, with no missing, extra, duplicate or changed source file. The final application source proof lives in `release-ready.json`, avoiding a self-referential source commit.

Evidence and source publication files are rechecked after the remote reads. The final Store copy is independently verified as an unsigned exact package, with complete evidence hashes in an exclusive readiness receipt. Partial failures remove only the two files in the newly owned output directory. Existing qualification flags remain unchanged; readiness does not claim submission. No signed package, certificate or private key enters the upload allowlist.

## Focused verification

Use the existing `env-qt6/bin/python` (Python 3.12) and `../../filequay/source/.tools/powershell-7.6.6/pwsh`; set `TMPDIR=/private/tmp` on macOS.

- `env-qt6/bin/python tools/msix/test_store_export.py -q`: 16 passed. Actual successful receipt shapes under both identities; failed/stale run and ownership fields; modified/missing facts, screenshots and modules; coherent file-oracle tampering; 71-source publication negatives; actual Git TAR modes/blob verification; complete real ZIP/restaging export; signed/coherently altered ZIP refusal; remote/source/evidence-race failure; incomplete cleanup; absent publication; owned partial-copy cleanup.
- `env-qt6/bin/python tools/msix/test_msix_qualification.py -q`: 24 passed.
- `env-qt6/bin/python tools/msix/test_workflow_files.py -q`: 10 passed.
- `env-qt6/bin/python -m pytest tools/msix/test_workflow_source_ui.py -q`: 8 passed.
- `env-qt6/bin/python tools/test_native_notices.py -q`: 6 passed.
- Separate PowerShell processes: `test_store_export_orchestration`, `test_qualify_msix_install`, `test_msix_evidence`, `test_registration_ownership`, `test_process_observation`, `test_window_evidence`, `test_defender_module`, `test_text_input_module`, `test_store_identity`, `test_temporary_ownership`, `test_workflow_helpers`, `test_workflow_observation`, `test_workflow_windows`: 13 passed. The new sequencing fixture executes the production loop for default, successful export, first/second install failure and export failure. Actual final reporting retains CI run/attempt under both modes.
- The unchanged `test_workflow_sendkeys.ps1` needs the actual Windows Forms parser and cannot execute on macOS. It remains required in Windows CI. `test_workflow_windows` ran its documented macOS ownership/native-interop replay, not its Windows Qt/IFileDialog execution.
- `git diff --check`: passed.

Initial shell `python3` was macOS Python 3.9 and lacked `hashlib.file_digest` for five existing domain workflow tests; rerunning with the documented Python 3.12 environment passed all ten. No compatibility workaround or product change was introduced.

Independent anonymous public-download check: exact manifest 38,006 bytes, SHA-256 `6ff1d996420954ece873f503794b348520a864575c6aba9772d177ccd726311a`. Actual prior-success public application archive: 1,972,681 bytes, SHA-256 `443c9190d60a4e24e99f77af41f94ac11bc2081655e8963acac4ab22aa873755`; all 722 tracked files/modes (6,787,142 source bytes) matched local base Git tree `032ea3a44952ad168f829a9b36f3975886c92b28`. This verifies the real GitHub archive route, not a new candidate Windows run.

## Remaining action

Root independently reviews and publishes this exact source snapshot, then runs the unchanged native build and both installed lifecycles with export enabled. Only that successful current run can produce the final unsigned Store artifact and readiness receipt. Source/assets publication is complete; Store submission and improved real Windows marketing captures remain separate root-coordinated actions. No parent status, site, snapshot or push was performed here.
