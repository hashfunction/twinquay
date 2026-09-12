# Supplemental native notices

`distribution/native-notices` contains **206 byte-verified source notice/declaration files (1,107,484 bytes)** plus `NOTICE-INDEX.json`. `native-notice-inputs.json` records the exact archive, member, destination, byte length and SHA-256 for each. The archives are the already acquired, verified inputs from `source-manifest.json`; no archive URL or version was guessed. This is a conservative collection, with optional/platform/build references explicitly distinguished from a claim of compiled inclusion.

The set supplies Qt's full SPDX license texts, the original source `qt_attribution.json` copyright/license/usage records, Wintab header terms, Qt PDF/PDFium references, Mesa 11.2.2 and LLVM 3.6.2 notices, both xxHash notices, Python externals, PyQt/SIP, pywin32 and PyInstaller notices. The original source collection remains intact; this supplementary map does not change the earlier run's manifest or notice-map hashes.

Reproduce into a **new** directory from the 79-input preparation cache (only the selected source archives are read):

```sh
python distribution/corresponding-source/prepare-native-notices.py --cache /path/to/downloads --output /path/to/new-native-notices
```

The archive collector checks every selected archive hash/length and every exact member before creating output. It streams archives and never executes them. `tools/native_notices.py` then checks the committed prepared tree against the map/index before copying it to `build/notices/source-notices`. Extra, absent or changed files fail packaging. Copies are rehashed. `tools/collect_notices.py` declares all these files in the actual dependency-notice inventory, so the existing stage and MSIX inventory gates cover their final bytes.

For a missing wheel notice, the collector may use only verified notices from that distribution's exact source version. This covers the five gaps measured in run 34675033643: sphinxcontrib-applehelp 2.0.0, devhelp 2.0.0, htmlhelp 2.1.0, qthelp 2.0.0 and serializinghtml 2.0.0. Their wheels omitted the copied license, while their acquired source distributions contain `LICENCE.rst`. An unknown/different version remains unresolved. This does not assert those build tools are frozen into the app.

## Actual frozen scope

The retained run-34675033643 PYZ proves the third-party Python roots: PyQt6; mutagen (48 modules); Send2Trash (12); semantic_version (2); xxhash (2); pywin32's pythoncom, pywintypes, pywin, win32com, commctrl, win32con, winerror and win32traceutil; and PyInstaller's `_pyi_rth_utils`. CPython modules and TwinQuay's own modules are also frozen. Distro is a packaging dependency, absent from this actual PYZ. Exact root/module counts are in `windows-system-baseline.json`. The full `pip freeze` remains a build-environment inventory, not a runtime bill of materials.

## Qt PDF attribution evidence and remaining boundary

The acquired QtWebEngine **6.11.2** source contains patched Chromium **140.0.7339.225** and PDFium revision **1afaa1a380fcd06cec420f3e5b6ec1d2ccb920dc**. All nine projects listed by the matching Qt PDF licensing page have source notice texts in this supplemental tree: PDFium, Chromium, Abseil, fast_float, FreeType, ICU, libjpeg-turbo, libpng and zlib. Nested PDFium source-license references are included conservatively as well. The declarations marked `Shipped: no` in `pdf-source-versions.json` retain that status. [Qt PDF 6.11.2 licensing](https://doc.qt.io/qt-6/qtpdf-licensing.html).

The exact source `src/pdf/CMakeLists.txt` defines `generate_pdf_attributions`, producing `pdf_attributions.qdoc` from GN target `:QtPdf` and the configured build directory. `src/pdf/configure.cmake` defaults V8 auto-detection off; XFA depends on V8, and its BMP/GIF/PNG/TIFF options depend on XFA. Those source defaults do **not** establish the original wheel's flags. The module also marks its third-party SBOM incomplete. A configured dependency/attribution output or equivalent verified original-build evidence is still needed to close the remaining completeness question; this collection does not fabricate such output. `REBUILD.md` describes how to retain it during a rebuild.

## Microsoft files still redistributed

The current baseline's version/signature observations identify six files at **14.44.35211.0**: the Qt wheel's MSVCP140, MSVCP140_1, MSVCP140_2, VCRUNTIME140 and VCRUNTIME140_1 plus pywin32's MFC140U. Python supplies two VCRUNTIME files at **14.42.34438.0**. All eight signatures were observed `Valid`, and all eight bytes match the exact comparison inputs. These facts establish origin/version, not license entitlement.

The exact Python source's `PC/crtlicense.txt` is now included and preserves the Windows binary redistribution conditions, expressly scoped to Microsoft Distributable Code. Microsoft's Visual Studio redistribution list covers VC redist files subject to its applicable license terms, and distinguishes prohibited debug runtime files. The final VC/MFC redistribution review must retain the applicable terms and entitlement; system-UCRT exclusion does not dispose of that separate review. [Microsoft redistribution list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution).

## Release status

Local preparation and staging checks passed; this notice payload has not yet been observed in a fresh Windows package. License clearance, corresponding-source publication and final unsigned Store export remain unclaimed. The final source release must include the exact modified application and preparation/build scripts, publish and verify the 71 source archives, preserve library replacement rights, and bind final package evidence to that publication. Historical qualification receipts remain unchanged.

The first Windows run of this notice update (34676892771) correctly refused the prepared tree: Git's Windows text checkout changed 204 of 206 original files to CRLF. A real local Git checkout with `core.autocrlf=true` reproduced those byte differences. The narrowly scoped `.gitattributes` rule now disables text conversion only under `distribution/native-notices`, preserving each upstream file's original LF or CRLF bytes. A regression performs the real Git add/Windows-style checkout and compares all 206 length/hash pairs. Source archive hashes and package validation remain unchanged; the corrected Windows package still requires a fresh run.
