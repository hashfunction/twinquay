# DupliSift real product screenshots

This dispatch-only pipeline photographs an unchanged, previously qualified Store package. It builds no product, changes no application preferences or behavior, and makes no new installation or Store acceptance claim.

The immutable input is public source `73f3842a2cc81aa3c69a5873a262517eae35b6f4`, successful Windows run `34683417158`, attempt `1`. Its Store artifact is `10295186168`; qualification metadata is `10294951513`. `DupliSift_1.0.1.0_x64.msix` is 46,032,604 bytes, SHA-256 `bf0ec697fd0eab1517c1ca42c530cb46fc057454ab74acbff1c05feb64d44ae7`. The 17,395-byte release receipt is pinned separately to SHA-256 `5d6c6485b3b9cf823af4b469878ee6ac88627fc17955b2e61e01d19179b788ec`.

`prepare_capture.py` checks the successful run, exact artifact identities, bounded regular ZIP members, original receipt/package bytes, both complete installed workflow records and every retained evidence file. It independently verifies the unsigned MSIX against all 600 original payload entries. The original export's six `runtime-profile/TwinQuay` entries were not uploaded by the qualification workflow; they are explicitly listed in `capture_checks.py` and are not claimed as capture inputs. The other 79 evidence files and the three source-publication records must match. Workflow source hashes use the original Windows checkout bytes, including Git's CRLF conversion; the capture checks out the exact historical source on Windows.

The native runner signs only an exclusive temporary copy with a nonexportable ephemeral key. It verifies the exact assigned registration, every installed file, retained process handle, package identity, executable hash and original module-origin policy. It creates marker-owned `%LOCALAPPDATA%\TwinQuay` and `C:\Demo` only when neither exists. Existing state, changed ownership markers and reparse paths are refused. The original source workflow appends `Cedar House Review` and prepares the same fictional project documents and byte oracles.

The original seven operations and nine proof screenshots run unchanged: prepare, scan, review, quarantine, collision, restore and finish. Only the oracle interpreter path, exclusive fixture parent and native window placement are adapted. Original owned surface recording must pass before any additional image. The native display is 1920×1080, and photographed windows are 1800×900 at 96 DPI. Display mode changes use enumerated modes, `CDS_TEST`, temporary flags and restoration of the retained original mode.

The three additional images are:

1. `01-scan-results.png`: real exact-content duplicate results and original document names.
2. `02-review-quarantine-plan.png`: the actual saved plan and chosen quarantine directory.
3. `03-restore-complete.png`: the real receipt reopened after the entire collision/recovery workflow. Its single row must expose the original path and `restored` status visibly through UIA, with its restore checkbox disabled. Opening the view must leave the restored bytes intact.

Each image is native GDI screen capture with no pixel alteration. Its receipt binds before/after window identity, title, PID, foreground HWND, dimensions, display, package and PNG hash. The run is successful only after normal zero-exit close, exact owned uninstall, certificate/key cleanup, marker-owned profile/demo cleanup, display restoration and an unchanged original unsigned package. The artifact includes PNG/JSON only, including original nine-stage evidence. Review `capture-result.json` before using any image from an incomplete run.

Run `.github/workflows/marketing-screenshots.yml` after review/publication. No package/run rebinding remains pending. Actual Windows UIA, native resize, display and visual-quality checks still require this fresh capture run.

Run capture in a fresh `pwsh -NoProfile -File tools/marketing/capture.ps1` host, as the dispatch workflow does. A nested script invocation hides required original functions from `GetNewClosure()` operations. [loader-repair-review.md](loader-repair-review.md) records the actual failure and unchanged-guard regression.
