# Rebuild and replace DupliSift's native dependencies

These instructions describe the supplied source and actual packaging boundary. The application has been built and run as a frozen Windows directory. **A modified Windows Qt/PyQt build has not been executed in this audit.** That is a distinct engineering verification, not a requirement to reproduce the vendor's original compiler output. The distribution supplies the source/recombine route in LGPLv3 section 4(d)(0): the complete corresponding library source, corresponding application code and build/install information under terms permitting recombination. No private signing key is needed to run a user-built unpackaged directory. The source materials must actually be published as described in `PUBLICATION.md`.

## Application and local native extensions

Use a user-owned fresh DupliSift checkout/source extraction on Windows x64. Retain the published source manifest and verify every archive with `materials.py`. The accepted historical build used Python **3.12.10**, setuptools **84.0.0**, wheel **0.48.0**, PyInstaller **6.22.2**, MSVC **14.51.36231** and Windows SDK **10.0.26100.0**. The workflow image was `windows-2025`. Compiler/linker commands, including `/MD`, are in run 34671787439's log. Visual Studio and the Windows SDK have separate terms; they are not contained in the source bundle.

From an x64 Visual Studio developer shell:

```powershell
py -3.12 -c "import sys,struct; assert sys.version_info[:3] == (3,12,10); assert struct.calcsize('P') == 8"
./tools/build-windows.ps1
./dist/DupliSift/DupliSift.exe
```

The first command intentionally checks the exact interpreter, since the `py -3.12` selector alone does not fix its patch release. `build-windows.ps1` requires a fresh checkout without `.venv`, installs the SHA-256-locked requirements, builds and tests the local C extensions, generates translations/help, runs Qt startup and creates `dist/DupliSift`. It also uses Git to identify the local source revision and PowerShell 7 (`pwsh`) for native metadata collection. If starting from the published source archive, initialize and commit that user-owned tree first (`git init`, `git add .`, `git commit` with your normal local Git identity); the release archive does not contain a private `.git` directory. The normal application executable needs no CI variables. The repository's `test-packaged-startup.ps1` is a separate CI-only qualifier, not a prerequisite for a user rebuild. This first build uses the published runtime wheels; it is **not** a rebuild of Qt/PyQt.

`setup.py` contains the complete three native extension inputs: `core/pe/modules/{block,cache,common}.c`, `common.h`, and `qt/pe/modules/block.c`. `build.py --clean` runs `setup.py build_ext --inplace`. `package.py --skip-nsis` executes the tracked `DupliSift.spec`, which excludes only the 44 reviewed Windows 10 system-library names and preserves the original Analysis/exclusion/import evidence. Its collector requires current-host system export resolution; see `WINDOWS-SYSTEM-LIBRARIES.md`. The recipe constructs the PyInstaller directory with `run.py`, original artwork, generated locale/help and notices. Follow the repository entry-script value if it changes. The installed qualifier is CI-only; do not bypass its existing user-profile/process/identity ownership checks on a personal machine.

## Build the shared Qt libraries

Extract the verified Qt **6.11.2** QtBase, QtSvg, QtImageFormats, QtTools, QtTranslations and QtWebEngine archives into separate source directories. The QtWebEngine source archive contains Qt PDF plus its exact patched Chromium/PDFium tree; a bare PDFium checkout is not a replacement. Use a local output prefix such as `C:\duplisift-rebuild\qt`, short paths, CMake >=**3.22** (the actual QtBase source minimum), Ninja, x64 MSVC and the Windows SDK. Qt PDF's source also invokes GN and requires the applicable WebEngine build prerequisites; use its pinned source `configure.cmake` checks as the authority. The source has its own GN code. Preserve the entire source tree, including `.cmake.conf`, CMake modules and license files.

A shared-library rebuild starts with QtBase's `configure.bat` and then uses the installed `qt-configure-module.bat` for each other module:

```bat
mkdir C:\duplisift-rebuild\qtbase-build
cd /d C:\duplisift-rebuild\qtbase-build
C:\sources\qtbase-everywhere-src-6.11.2\configure.bat -opensource -confirm-license -release -shared -nomake examples -nomake tests -prefix C:\duplisift-rebuild\qt
cmake --build . --parallel
cmake --install .

rem Repeat in separate build directories for qtsvg and qtimageformats:
C:\duplisift-rebuild\qt\bin\qt-configure-module.bat C:\sources\qtsvg-everywhere-src-6.11.2 -nomake examples -nomake tests
cmake --build . --parallel
cmake --install .
```

QtTools supplies `lrelease` for `.ts` → `.qm` regeneration; build its Linguist tools and then QtTranslations. Building the entire QtTools suite can introduce additional build dependencies that DupliSift does not distribute. Retain the resulting CMake options and module targets. To build PDF from QtWebEngine, explicitly select PDF and disable the WebEngine and PDF Quick/Widgets frontends if not required. Confirm the exact feature names in the supplied top-level/source configure files before invoking them; this audit does not fabricate a tested GN option string. The staged package includes `Qt6Pdf.dll` and `plugins/imageformats/qpdf.dll`, with `Qt6Network.dll`, but no QtWebEngine browser libraries, QML or multimedia libraries.

For a modified PDF build, retain `config.summary`, CMakeCache, generated `args.gn` and the **`generate_pdf_attributions`** output, because a changed configuration can change its third-party dependencies. Qt's `src/pdf/CMakeLists.txt` declares this target against the actual `:QtPdf` GN target. The matching vendor DLLs' original configure command, feature headers, generated attribution pages and source-revision evidence are now retained in `original-build-records` and described in `ORIGINAL-BUILD-EVIDENCE.md`. They disable V8/XFA and use a shared runtime. The above commands remain a source rebuild recipe, not a claim of binary-identical output. Neither LGPL 4(d)(0) nor this route requires reproducing the vendor's exact compiler toolchain or rebuilding unrelated permissive libraries.

Primary build references: [Qt Windows source build](https://doc.qt.io/qt-6/windows-building.html), [Qt WebEngine/PDF prerequisites](https://doc.qt.io/qt-6/qtwebengine-platform-notes.html). The supplied version-specific source checks take precedence if the rolling documentation changes.

## Build PyQt6 and SIP against that Qt

Use a separate Python 3.12.10 x64 build environment. The exact source inputs include SIP generator **6.15.0**, PyQt-builder **1.19.0**, setuptools-scm **8.3.1**, and the packaging/setuptools/wheel sources from the main lock. These supplemental generator versions satisfy PyQt6's actual `pyproject.toml`; they are a proposed rebuild toolchain, not a claim about Riverbank's original wheel compiler. Inspect and install their declared build dependencies before using `--no-build-isolation`.

1. Build/install `pyqt6_sip-13.12.0.tar.gz` with Python/pip in the replacement environment. Its `setup.py` compiles the supplied C files into `PyQt6.sip`.
2. Put the rebuilt Qt's `bin` directory first on `PATH`, and verify `qmake -query QT_VERSION` returns **6.11.2**.
3. Extract `pyqt6-6.11.0.tar.gz`, install the pinned SIP/PyQt-builder tools, and run `sip-install --confirm-license --qmake C:\duplisift-rebuild\qt\bin\qmake.exe --enable QtCore --enable QtGui --enable QtWidgets`. Check `sip-install --help` from the supplied generator when selecting other modules. Rebuilding those three bindings covers DupliSift's actual staged PyQt modules.
4. Verify the replacement environment imports all three bindings plus `PyQt6.sip`, reports PyQt **6.11.0**, Qt **6.11.2**, SIP runtime **13.12.0**, and runs the application's Qt tests.

[PyQt6's exact source distribution and build backend](https://pypi.org/project/PyQt6/6.11.0/) supplies both SIP interface definitions and helper implementation code. [PyQt-builder's bundle tool](https://pyqt-builder.readthedocs.io/en/stable/pyqtbundle.html) can package a local Qt installation, but its assumptions about official Qt installers must be reviewed when using a custom build.

## Other native libraries

- **CPython 3.12.10:** the full source has `PCbuild/readme.txt`, `PCbuild/build.bat` and `PCbuild/get_externals.bat`. Stage the pinned Python-maintained source dependencies at the names expected by `PCbuild/python.props`. The stock external helper otherwise downloads prebuilt OpenSSL/libffi binaries; supplying their source archives alone does not mean they were rebuilt. Follow the supplied `PCbuild/prepare_libffi.bat`/OpenSSL build instructions and preserve options/output libraries when choosing a complete interpreter rebuild. The official embedded ZIP is a private provenance reference, not source.
- **pywin32 311:** follow `build_env.md` at the pinned b311 commit, using x64 Python and Visual Studio/MFC components. Preserve all source license texts and Microsoft redistribution terms separately; do not run the global `pywin32_postinstall` inside the application virtual environment.
- **xxhash 3.8.1:** `python -m pip wheel --no-build-isolation --no-deps <extracted-source>` builds `src/_xxhash.c` and bundled `deps/xxhash/xxhash.c` by default. Leave `XXHASH_LINK_SO` unset to reproduce that linkage choice; bundled xxHash is 0.8.2.
- **PyInstaller 6.22.2:** supplied source includes `bootloader/` and its Waf build. Use the source's bootloader build instructions when modifying it, then install that modified PyInstaller in the packaging environment and rerun `package.py --skip-nsis`. The distribution exception is retained in `COPYING.txt`; the final executable necessarily differs from the template bootloader.
- **Mesa 11.2.2 / LLVM 3.6.2:** preserve historical NCSA/MIT notices. The exact upstream sources are available, but the Qt DLL's historical patch/build options are not reconstructed. The later [Qt Mesa wiki](https://wiki.qt.io/MesaLlvmpipe) describes a newer build procedure as well; do not apply its LLVM 5.0/Mesa 17.2 version numbers to this DLL. A replacement can be selected through Qt's software-OpenGL mechanism in a user-owned rebuild, subject to API/architecture testing.

## Recombine or replace without the Store signing key

Keep the release directory intact. Work on a **copy** of `dist/DupliSift` in a user-owned directory, or build it afresh from the modified source. The actual tracked `DupliSift.spec` uses PyInstaller's `EXE(..., exclude_binaries=True)` plus `COLLECT`, yielding external DLLs and plugins rather than linking Qt statically into the executable. Replace the coherent set of rebuilt Qt DLLs/plugins under `_internal/PyQt6/Qt6`, PyQt bindings under `_internal/PyQt6`, and any other modified libraries with matching architecture/ABI. Do not mix debug and release CRTs or partially replace an incompatible Qt set. The shipped application has no library hash/signature allowlist. The strict hash/source gates in the CI qualification tools protect release evidence; they are not executed by the normal application.

To re-freeze against a modified installation, first run `build-windows.ps1 -SkipPackage` in a fresh checkout, install the user-built SIP/PyQt libraries and coherent Qt installation into that checkout's `.venv`, then run `.venv/Scripts/python.exe package.py --skip-nsis`. The published SHA-256 lock documents the original application build; it does not revoke the user's right to replace dependencies. Preserve the modified source and notices, and re-run the Qt tests before packaging. The complete application source, resources and build scripts supply the corresponding application code.

Run `DupliSift.exe` from that copy. Useful engineering verification records the changed library hashes, actual loaded-module paths, startup, ordinary close and the consumer operations affected by the change. An untouched DLL copied to a new path or a passing test of an unrelated component is not evidence of running a modified Qt library. The MSIX signature protects a Store-installed directory; this source/unpackaged route remains available without the Store/private signing key and without terms prohibiting modification or reverse engineering for debugging library changes. LGPL section 4(e) calls for installation information only when and to the extent the incorporated GPL section 6 condition applies. A whole new Qt build or modification of the installed Store directory is not an additional condition stated by section 4(d)(0). **No successful modified-library Windows run is claimed here.**
