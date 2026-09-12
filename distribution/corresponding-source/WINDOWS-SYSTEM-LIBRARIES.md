# Windows system-library policy and evidence

The successful baseline is run **34675033643**, local source **e6c120930479592d424c9edb3db50877f760800f**. Both its disposable and fixed Store installations passed the real scan/quarantine/conflict/restore workflow, normal close and owned uninstall. Its **114** native collector origins are retained in `native-build-provenance.json` in the run artifact. `windows-system-baseline.json` binds the exact metadata/TOC files by hash and supplements the earlier 34671787439 audit; it does not rewrite either run's evidence.

The newer baseline proves that **43 API-set forwarder DLLs plus `ucrtbase.dll`** came from `C:\hostedtoolcache\windows\Java_Temurin-Hotspot_jdk\17.0.20-101\x64\bin`. These are incidental dependency-search results. The JDK path alone provides no redistribution entitlement.

## Why this package can use Windows' copies

Both MSIX identity modes already require `Windows.Desktop` **10.0.19041.0**. Microsoft's UCRT deployment documentation says the UCRT is an operating-system component included in Windows 10 and later; on those systems Windows uses its system copy even when an application ships another copy. The documented local forwarders exist to support older systems. [Microsoft UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170).

The exact **PyInstaller 6.22.2** `depend/dylib.py` includes `api-ms-win-core.*`, `api-ms-win-crt.*` and `ucrtbase.dll` for downlevel Windows compatibility and explicitly notes that they need not be bundled for a Windows 10-or-later target. This project applies a narrower, enumerated **44-name** policy at its own spec boundary. VC/MFC and all other binaries remain unchanged. [Pinned PyInstaller source](https://github.com/pyinstaller/pyinstaller/blob/v6.22.2/PyInstaller/depend/dylib.py#L139).

An API-set name denotes a loader contract, not necessarily a physical DLL. A prefix alone does not establish availability, and a load alone does not prove every requested implementation. The build therefore tests actual imported exports using the system loader, including forwarded functions. [Microsoft API sets](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets).

## Actual imported symbols

The previously acquired wheel/CPython comparison archives contain **66** native files whose exact bytes match this run. The production `read_imports` helper parsed all 66 with the already locked **pefile 2024.8.26**, including normal and delay-load tables and ordinal imports. The compact record retains every imported library/count/symbol-list hash and all selected OS-contract symbol names. These binaries reference **15 of the 44 selected names**, comprising **347 distinct DLL/symbol pairs**:

- All 14 selected `api-ms-win-crt-…-l1-1-0.dll` contracts.
- `Qt6Core.dll` delay-imports `WaitOnAddress`, `WakeByAddressSingle` and `WakeByAddressAll` through `api-ms-win-core-synch-l1-2-0.dll`. Microsoft lists that contract for Windows 8 and later. [WaitOnAddress requirements](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitonaddress).

The other 28 selected core forwarders have no direct importers among those 66 files. They were collected during transitive dependency analysis; this audit has not inspected the unavailable JDK binary import tables. Python's `api-ms-win-core-path-l1-1-0` and Qt's WinRT contracts were already OS-resolved, absent from the staged payload, and are **not** new exclusions. MFC's legitimate `winspool.drv` imports are retained in the evidence as well.

Four locally generated native binaries and the 44 excluded JDK binaries were not uploaded by the metadata-only workflow. Their actual import tables will be recorded by the next Windows build; this local audit does not invent them.

## Implementation and fresh-run gates

`TwinQuay.spec` retains the original Analysis TOC, filters only the reviewed exact root binary names, and writes their original paths/hashes/lengths to `windows-system-exclusions.json` before constructing COLLECT. A duplicate, nested alias, unexpected type/source filename or different minimum Windows version fails the policy. Unknown library names are retained for review, not automatically omitted. Package resources, windowed mode and the two installed identity modes stay the same.

`collect_build_evidence.py` independently rederives the exclusion record from the saved Analysis and current original bytes. It rejects any selected OS library remaining anywhere in the stage. It continues to require exact COLLECT/native inventory equality and original/staged byte equality. Every retained and excluded native original now has its normal/delay imports recorded, alongside PE headers, version and Authenticode metadata. The spec, helper, package script, identity/minimum source and lock are hashed in the build evidence.

Before writing the final native evidence, the Windows collector resolves **all 44 reviewed names** through `LoadLibraryExW(..., LOAD_LIBRARY_SEARCH_SYSTEM32)`. For each selected contract actually imported by a retained native binary, it resolves every name/ordinal with `GetProcAddress`, including delay imports, and checks each export's owning module with `GetModuleHandleExW`. All resolved modules must be in the actual Windows system directory. Missing contracts, exports or foreign owners fail the build. Resolved OS host files receive the same hash/version/signature observations as native input files; no OS binary is copied into the package.

The existing installed module/path/ownership/foreground/consumer/cleanup checks and metadata-only upload policy are unchanged. A fresh full Windows run is required. If the dependency graph is unchanged, **70 retained native files** are expected; that number is a prediction, not a completed package measurement. The Windows-2025 runner cannot establish actual execution on Windows 10 build 19041. The minimum-version rationale above and current-host symbol proof are distinct from a minimum-OS execution test.

## Remaining release work

Excluding the 44 OS files removes the need to redistribute those JDK copies. It does not clear the **VC/MFC** files still shipped from the exact Qt/Python/pywin32 inputs, complete native third-party notices, publish source, demonstrate a Qt/PyQt replacement build, or authorize binary export. Historical `license_clearance=false`, `corresponding_source_published=false` and qualification-only receipts remain accurate. Final source publication and package readiness require separate verified records.
