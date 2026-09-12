# Copyright 2026 Trieflow LLC. MIT.
"""Exact Windows 10 OS components; keep VC/MFC and every other runtime.

Reviewed against run 34675033643; see distribution/corresponding-source/
WINDOWS-SYSTEM-LIBRARIES.md. No prefix implies eligibility for exclusion.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path, PureWindowsPath
import sys

from msix.msix_qualification import file_record

MINIMUM_WINDOWS = "10.0.19041.0"
SYSTEM_LIBRARIES = frozenset({
    'api-ms-win-core-console-l1-1-0.dll',
    'api-ms-win-core-datetime-l1-1-0.dll',
    'api-ms-win-core-debug-l1-1-0.dll',
    'api-ms-win-core-errorhandling-l1-1-0.dll',
    'api-ms-win-core-fibers-l1-1-0.dll',
    'api-ms-win-core-fibers-l1-1-1.dll',
    'api-ms-win-core-file-l1-1-0.dll',
    'api-ms-win-core-file-l1-2-0.dll',
    'api-ms-win-core-file-l2-1-0.dll',
    'api-ms-win-core-handle-l1-1-0.dll',
    'api-ms-win-core-heap-l1-1-0.dll',
    'api-ms-win-core-interlocked-l1-1-0.dll',
    'api-ms-win-core-kernel32-legacy-l1-1-1.dll',
    'api-ms-win-core-libraryloader-l1-1-0.dll',
    'api-ms-win-core-localization-l1-2-0.dll',
    'api-ms-win-core-memory-l1-1-0.dll',
    'api-ms-win-core-namedpipe-l1-1-0.dll',
    'api-ms-win-core-processenvironment-l1-1-0.dll',
    'api-ms-win-core-processthreads-l1-1-0.dll',
    'api-ms-win-core-processthreads-l1-1-1.dll',
    'api-ms-win-core-profile-l1-1-0.dll',
    'api-ms-win-core-rtlsupport-l1-1-0.dll',
    'api-ms-win-core-string-l1-1-0.dll',
    'api-ms-win-core-synch-l1-1-0.dll',
    'api-ms-win-core-synch-l1-2-0.dll',
    'api-ms-win-core-sysinfo-l1-1-0.dll',
    'api-ms-win-core-sysinfo-l1-2-0.dll',
    'api-ms-win-core-timezone-l1-1-0.dll',
    'api-ms-win-core-util-l1-1-0.dll',
    'api-ms-win-crt-conio-l1-1-0.dll',
    'api-ms-win-crt-convert-l1-1-0.dll',
    'api-ms-win-crt-environment-l1-1-0.dll',
    'api-ms-win-crt-filesystem-l1-1-0.dll',
    'api-ms-win-crt-heap-l1-1-0.dll',
    'api-ms-win-crt-locale-l1-1-0.dll',
    'api-ms-win-crt-math-l1-1-0.dll',
    'api-ms-win-crt-multibyte-l1-1-0.dll',
    'api-ms-win-crt-process-l1-1-0.dll',
    'api-ms-win-crt-runtime-l1-1-0.dll',
    'api-ms-win-crt-stdio-l1-1-0.dll',
    'api-ms-win-crt-string-l1-1-0.dll',
    'api-ms-win-crt-time-l1-1-0.dll',
    'api-ms-win-crt-utility-l1-1-0.dll',
    'ucrtbase.dll',
})


def filter_binaries(binaries, minimum_version):
    if minimum_version != MINIMUM_WINDOWS:
        raise ValueError('OS-library exclusion requires the reviewed Windows 10 19041 minimum')
    kept, excluded, seen = [], [], set()
    for row in binaries:
        name, source, typecode = row
        destination = PureWindowsPath(name)
        base = destination.name.lower()
        if base not in SYSTEM_LIBRARIES:
            kept.append(row)
            continue
        if (len(destination.parts) != 1 or destination.drive or destination.root or
                typecode != 'BINARY' or not source or PureWindowsPath(source).name.lower() != base or base in seen):
            raise ValueError('Unexpected OS-library destination, source name, type or duplicate')
        path = Path(source)
        if not path.is_absolute():
            raise ValueError('OS-library original must be absolute')
        seen.add(base)
        excluded.append(dict(name=name, source=source, typecode=typecode, **file_record(path)))
    return kept, dict(schema_version=1, minimum_windows=minimum_version,
                      policy_names=sorted(SYSTEM_LIBRARIES), excluded=excluded,
                      release_ready=False, scope='Removed from COLLECT; original Analysis retained; Windows system import proof required')


def read_imports(path):
    # This is already a hash-locked Windows build dependency of PyInstaller.
    import pefile
    if pefile.__version__ != '2024.8.26':
        raise ValueError('PE import parser differs from audited pefile 2024.8.26')
    try:
        with pefile.PE(str(path), fast_load=True) as pe:
            pe.parse_data_directories(directories=[1, 13])
            result = []
            for key, delay, directory in [('DIRECTORY_ENTRY_IMPORT', False, 1), ('DIRECTORY_ENTRY_DELAY_IMPORT', True, 13)]:
                groups = getattr(pe, key, [])
                if pe.OPTIONAL_HEADER.DATA_DIRECTORY[directory].VirtualAddress and not groups:
                    raise ValueError('PE import directory could not be parsed')
                for group in groups:
                    name = group.dll.decode('ascii').lower()
                    if PureWindowsPath(name).name != name or not name.endswith(('.dll', '.drv')):
                        raise ValueError('Unexpected PE imported library name')
                    symbols = [item.name.decode('ascii') if item.name else {'ordinal': item.ordinal} for item in group.imports]
                    if not symbols:
                        raise ValueError('PE import descriptor has no symbols')
                    result.append(dict(dll=name, delay=delay, symbols=symbols))
            return result
    except (pefile.PEFormatError, UnicodeError, IndexError, AttributeError) as exc:
        raise ValueError(f'Invalid PE imports: {path}') from exc


class WindowsSystemResolver:
    """Load only system DLLs and prove every requested export's owning module."""
    def __init__(self):
        if sys.platform != 'win32' or sys.getwindowsversion()[:3] < (10, 0, 19041):
            raise ValueError('System resolution requires Windows 10 19041 or later')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        for name, restype, argtypes in [
            ('GetSystemDirectoryW', wintypes.UINT, [wintypes.LPWSTR, wintypes.UINT]),
            ('LoadLibraryExW', wintypes.HMODULE, [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]),
            ('GetModuleFileNameW', wintypes.DWORD, [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]),
            ('GetProcAddress', ctypes.c_void_p, [wintypes.HMODULE, ctypes.c_void_p]),
            ('GetModuleHandleExW', wintypes.BOOL, [wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.HMODULE)]),
            ('FreeLibrary', wintypes.BOOL, [wintypes.HMODULE]),
        ]:
            fn = getattr(self.kernel, name); fn.restype = restype; fn.argtypes = argtypes
        buffer = ctypes.create_unicode_buffer(32768)
        count = self.kernel.GetSystemDirectoryW(buffer, len(buffer))
        if not count or count >= len(buffer):
            raise ValueError('Cannot identify actual Windows system directory')
        self.system_directory = Path(buffer.value).resolve(strict=True)

    def module_path(self, module):
        buffer = ctypes.create_unicode_buffer(32768)
        count = self.kernel.GetModuleFileNameW(module, buffer, len(buffer))
        if not count or count >= len(buffer):
            raise ValueError('Cannot identify resolved system module')
        path = Path(buffer.value).resolve(strict=True)
        if path.parent != self.system_directory:
            raise ValueError(f'OS contract/export resolved outside Windows system directory: {path}')
        return str(path)

    def __call__(self, name, symbols):
        if name not in SYSTEM_LIBRARIES:
            raise ValueError('Unreviewed system contract')
        handle = self.kernel.LoadLibraryExW(name, None, 0x00000800)  # LOAD_LIBRARY_SEARCH_SYSTEM32
        if not handle:
            raise ValueError(f'Windows system contract unavailable: {name}')
        try:
            hosts = {self.module_path(handle)}
            for symbol in symbols:
                if isinstance(symbol, str):
                    arg = ctypes.cast(ctypes.c_char_p(symbol.encode('ascii')), ctypes.c_void_p)
                else:
                    ordinal = symbol['ordinal']
                    if not isinstance(ordinal, int) or not 1 <= ordinal <= 65535:
                        raise ValueError('Invalid imported ordinal')
                    arg = ctypes.c_void_p(ordinal)
                address = self.kernel.GetProcAddress(handle, arg)
                if not address:
                    raise ValueError(f'Windows system symbol unavailable: {name}!{symbol}')
                owner = wintypes.HMODULE()
                if not self.kernel.GetModuleHandleExW(0x6, address, ctypes.byref(owner)):
                    raise ValueError(f'Cannot identify system export owner: {name}!{symbol}')
                hosts.add(self.module_path(owner))
            return dict(dll=name, symbols=symbols, host_paths=sorted(hosts))
        finally:
            if not self.kernel.FreeLibrary(handle):
                raise ValueError(f'Cannot release OS-contract observation handle: {name}')


def verify_system_resolution(native, resolver):
    requested = {name: {} for name in SYSTEM_LIBRARIES}
    for row in native:
        for group in row['imports']:
            if group['dll'] in requested:
                for symbol in group['symbols']:
                    requested[group['dll']][json.dumps(symbol, sort_keys=True)] = symbol
    return [resolver(name, [symbols[key] for key in sorted(symbols)]) for name, symbols in sorted(requested.items())]
