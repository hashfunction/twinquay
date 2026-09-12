# DupliSift marketing capture host repair

Base: `0af808e9a62b420228458f296ddba9db89e93512`. Actual failure: Windows capture `34685025584`. Its original package remains the successful Store-qualified run `34683417158`, public source `73f3842a2cc81aa3c69a5873a262517eae35b6f4`, SHA-256 `bf0ec697fd0eab1517c1ca42c530cb46fc057454ab74acbff1c05feb64d44ae7`.

Evidence under `/private/tmp/duplisift-marketing-34685025584-review/DupliSift-real-product-screenshots` shows that exact package/input verification, signing, registration, activation, native title/1800×900 geometry, and 126 loaded modules passed. The original process guard was therefore already present and had run. `Prepare` subsequently failed at qualified `tools/msix/qualify-workflow.ps1:542` with `CommandNotFoundException` for `Assert-TwinQuayWorkflowProcess`, before any completed workflow stage or fixture file. No marketing images were accepted. Cleanup left no errors or package registrations; retained-process cleanup completed with exit -1. Normal-close/uninstall acceptance remained false, as expected on capture failure.

The cause is host scope, not a `LibraryOnly` omission. `Assert-TwinQuayWorkflowProcess` is unconditionally defined in `qualify-workflow.ps1:135`, imported by the installer at line 468. The workflow's previous `./tools/marketing/capture.ps1` call ran a nested script inside Actions' generated PowerShell script. The original operations use `GetNewClosure()`, whose dynamic module could not resolve functions defined only in that nested script scope. The original qualifier itself launches a fresh `pwsh -File` process, where those dependencies remain available.

The failure was reproduced locally with the unchanged production loader, guard, workflow entrypoint, core and Prepare closure. Running the probe as a nested script produced the exact native missing-command error. Running that same probe in a fresh `pwsh -File` host executed the actual guard and correctly refused a deliberately unowned process with `The original owned installed process is no longer live.` Neither run created any demo/consumer file or proceeded beyond Prepare.

The fix changes the dispatch step to the same fresh checked `pwsh -File` host used by the original qualifier. It propagates a nonzero child exit as capture failure. The four unchanged loader statements were moved into `capture_library.ps1`, used by both real capture and its fixture, so the regression cannot substitute a copied or stub process guard. No original qualification, application, module, input, oracle, lifecycle, package, source-publication or acceptance code changed.

`test_capture_loader.ps1` executes the production loader in both host modes. It checks the guard's actual source file, the original Prepare/core refusal and error stack, zero completed stages, no fixture creation, restored signing directory and cleared capture interpreter. The positive case also resolves all 13 required original/capture dependencies from a real closure. The workflow runs this fixture against its exact historical `qualified-source` checkout before installation. The earlier adapter seam fixture remains useful but had replaced the guard and was invoked directly with `-File`; it did not exercise the production nested host and could not detect this failure.

Validation completed:

```text
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File tools/marketing/test_capture_loader.ps1 -QualifiedSource /private/tmp/duplisift-capture-qualified-crlf
# PASS old nested-host failure + fresh-host actual guard + 13 closure dependencies
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File tools/marketing/test_capture_adapter.ps1 -Python <this source>/env-qt6/bin/python
# PASS original adapter/oracle/failure restoration
../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File tools/marketing/test_capture_helpers.ps1
../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File tools/marketing/test_display_modes.ps1
# Both PASS
./env-qt6/bin/python -m unittest discover -s tools/marketing -p 'test_*.py' -v
# 7 PASS
```

The regression first rejected the unchanged workflow's nested launch, then passed with the checked fresh host. Every marketing PowerShell file parsed and `git diff --check` passed. Fresh native Windows capture remains necessary for actual UI interactions, images, normal close and successful capture cleanup; local scope replay is not screenshot acceptance. No push or site, parent, Store or product edits were performed.
