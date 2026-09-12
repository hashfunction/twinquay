# Qt 6 runtime qualification

Historical qualification record. Current DupliSift naming, compatibility and screenshot fixtures are documented in [the rename review](duplisift-rename-review.md). Old run titles, package paths and source commits below remain unchanged.

Checked 2026-09-11 against primary publisher documentation. The runtime is now
PyQt6 6.11.0, PyQt6-Qt6 6.11.2 and PyQt6-sip 13.12.0, pinned in requirements,
package metadata and the hash-locked Windows dependency file. Qt's
[release table](https://doc.qt.io/qt-6/qt-releases.html) lists 6.11.2 as the
current 6.11 patch, with standard support through 2027-03-17. Its usual public
patch schedule follows the current minor release; no commercial LTS or extended
security entitlement is assumed. Review newer maintenance releases before every
binary release. The retired public Windows Qt 5.15.2 wheel is no longer used.

Sources and licensing:

- [Riverbank](https://www.riverbankcomputing.com/software/pyqt) supplies GPLv3
  PyQt wheels with LGPL Qt. TwinQuay continues to use the GPL distribution.
- [PyQt6 6.11.0](https://pypi.org/project/PyQt6/6.11.0/),
  [Qt 6.11.2](https://pypi.org/project/PyQt6-Qt6/6.11.2/), and
  [SIP 13.12.0](https://pypi.org/project/PyQt6-sip/13.12.0/) provide the pinned
  CPython-compatible Windows x64 and development-host wheels. SIP uses BSD-2-Clause.
- [Qt 6.11 Windows configurations](https://doc.qt.io/qt-6/windows.html) list
  Windows 10 1809+, Windows 11 x64 and MSVC 2022. These are upstream runtime
  configurations, not evidence of TwinQuay's own minimum-OS acceptance.

The port uses scoped Qt 6 enums, QAction in QtGui, current dialog/screen APIs,
Qt enum values in portable preference serialization, and explicit checkbox
states. Restored dock areas are converted back to Qt enums. Image pan and folder
selection retain their behavior. No Qt5/PyQt5 compatibility shim is bundled.

Original artwork is now loaded through `qt.resources.asset_path` from source or
PyInstaller's data root. The package explicitly includes `images/twinquay`.
This removes dependence on the retired pyrcc5 resource generator and avoids
adding a second Qt distribution solely as a build tool. The image manifest is
small and inspectable; tests decode every asset in both source/package layouts.

The native image path is unchanged: `qt.pe.photo.File` converts QImage to RGB888,
then the existing C extension obtains `bits().ascapsule()` and honors row stride.
A native-backed regression checks exact RGB values for padded rows and the real
PNG/rotated-image scan path, rather than only accepting extension imports.

Local evidence (macOS ARM64, Python 3.12.7): clean build of all three native
extensions, translations, original assets and local help. Runtime smoke reports
Qt 6.11.2, PyQt 6.11.0, binding compile Qt 6.11.0. Existing headless tests failed
collection under the Qt6-only environment before the port. Added behavior tests
caught saved integer dock areas and unchecked enum values, then folder/pan API
removals. After repair, 13 headless tests pass, including all three scan modes,
a real Contents scan through results/evidence publication and marking, cleanup
selection, recoverable receipts, settings import and native image comparisons.
The complete core + hscommon + Qt suite passes 579 tests, with one native
xattr skip on this macOS Python. Dependency consistency and changed-code
undefined-name/syntax checks pass. No modifications were made to core
scan-result/evidence publishing.

Windows qualification must run `./tools/build-windows.ps1` from a fresh checkout.
The lock and package inventory now require Qt6Core/qwindows/original assets and
reject a package containing Qt5 DLLs. Only a Windows runner can confirm the
Windows native build, headless tests and PyInstaller staging. Interactive
keyboard/DPI/screenshots, locked/second-volume filesystem behavior, install,
upgrade/uninstall, signing, Store submission and full Qt/plugin/source/license
fulfillment remain release gates. None is inferred from these macOS checks.
