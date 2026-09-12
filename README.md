# DupliSift

DupliSift is Trieflow LLC's Windows duplicate-discovery application, based on
[dupeGuru 4.3.1](https://github.com/arsenetar/dupeguru/tree/4.3.1) at
`1f1dfa88dc5f6ffe13f4de514c884ab9c83bd7ce`. It preserves the upstream scanner,
reference groups, marking, details, filtering and result review while adding
reviewable cleanup plans, fresh full-byte checks, recoverable quarantine and
verified restore.

[Product](https://duplisift.trieflow.com) ·
[Privacy](https://duplisift.trieflow.com/privacy) ·
[Support](https://duplisift.trieflow.com/support) ·
[Source](https://duplisift.trieflow.com/source)

**Status:** source implementation and local Python 3.12 checks are available.
Windows build, native filesystem acceptance, Qt redistribution review, signed
MSIX, Store identity/submission and canonical website release gates are pending.
A local macOS test or offscreen Qt startup is not Windows certification.

## Reviewable cleanup

Run a **Contents** scan, inspect references, mark duplicates and choose **Review
Cleanup Plan…**. Each row shows the duplicate, reference, evidence, eligibility,
bytes and exact planned destination. Choose a quarantine folder and selected
rows before starting the background verification job. Save a JSON plan if needed.
Similarity results and previously saved result files have no authority to move
files; rescanning in Contents mode is required. Files are compared byte-for-byte
at execution, independent of scan hashes. Missing/changed/read-only files,
folders, links, reparse points, cloud placeholders and detected extra metadata
are refused.

Quarantine preserves a versioned plan, write-ahead receipt, payload paths, size
and SHA-256 recovery checksums. Cancellation stops before the next item and
keeps the receipt for completed work. Open **Quarantine Receipts…** from the File
menu even after restarting; restore chosen items only. Restore refuses occupied
original paths and changed payloads. Nothing automatically empties quarantine.
New result and directory-list files use `.duplisift` and `.duplisiftdirs`;
existing `.twinquay`, `.twinquaydirs` and upstream dupeGuru files remain readable.

See [user help](help/duplisift/index.html) and [recovery details](docs/cleanup-recovery.md).

Windows application data is `%LOCALAPPDATA%\TwinQuay`; quarantine remains in the
folder the user chooses. Optional portable mode requires `DupliSift.ini` beside
the executable and uses `data/TwinQuay`. Existing `TwinQuay.ini` portable
settings take precedence when present; both data locations remain compatible
with earlier releases. Legacy dupeGuru preferences are kept separate. The
explicit import action copies a typed subset of scan settings from a chosen
INI; it excludes custom commands and application identity.

## Development and Windows handoff

The current runtime is PyQt6 6.11.0 with Qt 6.11.2 and SIP 13.12.0; see
[runtime qualification](docs/qt6-runtime-migration.md).

Use a fresh checkout, Python 3.12 x64 and Visual Studio 2022 C++ Build Tools with
Windows SDK. Run the following in PowerShell from the source directory:

```powershell
./tools/build-windows.ps1
```

The script creates an isolated venv, installs the hash-locked Windows toolchain,
builds three native extensions, validates original assets and copies local help, runs core and Qt tests, executes
an offscreen native/image smoke, and stages `dist/DupliSift` with PyInstaller.
`package.py --skip-nsis` produces the directory for root-owned MSIX work; NSIS
is optional and parameterized. See [Windows qualification](docs/windows-build.md)
and the **unpublished draft** [CI workflow](docs/windows-build-workflow.yml).
Never reuse an upstream signing identity or treat a staged EXE as a tested MSIX.

On a local development host:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-extra.txt setuptools wheel
.venv/bin/python build.py --clean
.venv/bin/python -m pytest core hscommon -q
.venv/bin/python -m pytest qt/tests -q
.venv/bin/python tools/smoke-qt.py
```

## License and provenance

GPLv3. The upstream authors' copyrights, file-level notices, GPL text and git
history are retained. DupliSift modifications and active icons are copyright
2026 Trieflow LLC. Recipients retain GPL rights. See [LICENSE](LICENSE),
[THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt), and the preserved
[upstream README](docs/upstream-README.md). Distribute corresponding modified
source, build scripts and full dependency notices with any binary release.
The exact bundled Qt/plugin license/source inventory remains a release gate.
