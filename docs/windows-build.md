# Windows Python 3.12 qualification handoff

Target: Python 3.12 x64, Visual Studio 2022 C++ Build Tools, Windows SDK,
PyQt6 6.11.0, Qt 6.11.2, SIP 13.12.0, PyInstaller 6.22.2, pytest 8.4.2. A fresh Windows runner must execute
`./tools/build-windows.ps1`; no Windows build was executed on the macOS authoring
host. `docs/windows-build-workflow.yml` is an unpublished draft. Root owns CI
publication, action-SHA pinning, Store/MSIX identity, signing and release records.

The prerequisite investigation reproduced:

1. `build.py --modules`: setuptools 84 removed `setuptools.sandbox`; replaced
   with a checked `sys.executable setup.py build_ext --inplace` subprocess.
2. PyInstaller 4.5.1: startup failed importing removed `pkg_resources`; upgraded
   to 6.22.2. The upstream pytest 6 constraints were replaced with pytest 8.4.2.
3. `hscommon.pygettext` imported removed `imp`; migrated source discovery to
   `importlib.machinery.PathFinder`, including Python 3 directory walking.
4. PyInstaller resource paths depended on CWD/`__file__` existence; updated to
   `_MEIPASS`, with a regression test. Original assets now load from explicit
   source/package paths without a Qt5 resource generator.

Current local authoring evidence: Python 3.12.7, macOS ARM64 Clang, PyQt 6.11.0,
Qt runtime 6.11.2 (`QT_VERSION_STR` binding compile version 6.11.0), PyInstaller
6.22.2. All three C extensions compiled and imported locally. `build.py --clean`
builds extensions, translations, validates original images and copies DupliSift's
maintained local help. The upstream Sphinx documentation remains in source.
See [runtime migration and primary references](qt6-runtime-migration.md) and
[Windows filesystem repair](windows-file-identity-repair.md). Real Windows runs
compiled the previous Qt5 build but exposed quarantine failures; that evidence
does not qualify this Qt6 migration or the filesystem repair.

The Windows lock `tools/python-windows-lock.txt` was resolved with hashes using:

```sh
uv pip compile --python-version 3.12 --python-platform x86_64-pc-windows-msvc --generate-hashes tools/build-requirements.txt -o tools/python-windows-lock.txt
```

This is a **resolved lock**, not an installed Windows inventory. It includes
PyQt6-Qt6 6.11.2. Root must review the exact DLL/plugin licensing and current
maintenance release before release. Official wheel availability proves package
availability, not fitness or redistribution compliance.

Windows commands (fresh checkout; script deliberately refuses an existing venv):

```powershell
./tools/build-windows.ps1
# Or build/test without package staging:
./tools/build-windows.ps1 -SkipPackage
# After a successful build:
.venv/Scripts/python.exe package.py --skip-nsis
# Optional standalone NSIS, root MSIX workflow does not require this:
.venv/Scripts/python.exe package.py --nsis-path 'C:\Program Files (x86)\NSIS\makensis.exe'
```

Expected outputs: `dist/DupliSift/DupliSift.exe`, PyInstaller `_internal` directory,
Qt platform/imageformats DLLs, GPL and collected notices; `build-evidence` test
XML, freeze and exact SHA-256 package inventory. `package_inventory.py` fails
if DupliSift.exe or qwindows.dll is absent. Missing docs, resource build, compiler,
PyInstaller or NSIS commands fail explicitly. No hardcoded upstream account,
signing service, Store package identity or publisher ID is used.

Native acceptance still required:

- Clean Windows build and imports of core.pe._block/core.pe._cache/qt.pe._block_qt.
- Packaged interactive launch, scan/review, cleanup and restore; Qt plugin checks.
- Unicode and >260-character paths, ACL/read-only/locked files, exclusive-source
  handle deletion, NTFS alternate streams, junctions/symlinks, OneDrive offline
  and recall placeholders, actual second-volume copy/restore, low disk space.
- Cancel after an item, crash after write-ahead checkpoints, restart from receipt,
  restore collisions and concurrent file changes (preserve all unexpected data).
- Keyboard navigation, 100/150/200% scaling, real screenshots, MSIX install,
  upgrade and uninstall while preserving application data/quarantine.
- Full Qt/plugin/CRT/Python/native helper licenses and source delivery audit.
- Canonical product/privacy/support site HTTP 200, DNS/SSL, Store identity and
  signed package/certification, all managed by root.

Primary compatibility references:
[PyQt6 wheel and GPL metadata](https://pypi.org/project/PyQt6/),
[PyInstaller requirements](https://pyinstaller.org/en/stable/requirements.html),
[setuptools history](https://setuptools.pypa.io/en/latest/history.html),
[FindFirstStreamW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findfirststreamw),
[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle).
