# Copyright 2026 Trieflow LLC. MIT.
"""Exercise the production freezer policy, PE reader and OS-resolution boundary."""
import ctypes
import json
import struct
from types import SimpleNamespace
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
from windows_system_libraries import SYSTEM_LIBRARIES, MINIMUM_WINDOWS, filter_binaries, read_imports, verify_system_resolution, WindowsSystemResolver
from msix.msix_qualification import file_record


class SystemLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.dll = self.root / 'ucrtbase.dll'
        self.dll.write_bytes(b'fixture')

    def test_only_exact_reviewed_names_removed_and_all_other_entries_preserved(self):
        rows = [(name, str(self.root / name), 'BINARY') for name in sorted(SYSTEM_LIBRARIES)]
        kept = [('VCRUNTIME140.dll', str(self.root / 'VCRUNTIME140.dll'), 'BINARY'),
                ('PyQt6/Qt6/bin/MSVCP140.dll', str(self.root / 'MSVCP140.dll'), 'BINARY'),
                ('api-ms-win-core-new-l9-9-9.dll', '/unreviewed.dll', 'BINARY'),
                ('data.txt', '/data.txt', 'DATA')]
        with patch('windows_system_libraries.file_record', return_value={'bytes': 7, 'sha256': 'a'*64}):
            actual, record = filter_binaries(rows + kept, MINIMUM_WINDOWS)
        self.assertEqual(actual, kept)
        self.assertEqual(len(record['excluded']), 44)
        self.assertEqual({r['name'] for r in record['excluded']}, SYSTEM_LIBRARIES)
        self.assertFalse(record['release_ready'])

    def test_wrong_minimum_nested_alias_wrong_source_or_type_rejected(self):
        for row in [('vendor/ucrtbase.dll', str(self.dll), 'BINARY'),
                    ('ucrtbase.dll', str(self.root / 'other.dll'), 'BINARY'),
                    ('ucrtbase.dll', str(self.dll), 'DATA')]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                filter_binaries([row], MINIMUM_WINDOWS)
        with self.assertRaises(ValueError):
            filter_binaries([], '10.0.17763.0')
        with self.assertRaises(ValueError):
            filter_binaries([('ucrtbase.dll',str(self.dll),'BINARY')]*2, MINIMUM_WINDOWS)

    def test_empty_policy_result_allowed_without_inventing_excluded_origins(self):
        kept, record = filter_binaries([], MINIMUM_WINDOWS)
        self.assertEqual(kept, [])
        self.assertEqual(record['excluded'], [])

    def test_import_reader_rejects_invalid_or_truncated_pe(self):
        with self.assertRaises(ValueError):
            read_imports(self.dll)

    def test_actual_pe_regular_and_delay_import_tables_include_named_and_ordinal_symbols(self):
        from test_collect_build_evidence import pe_bytes
        raw = bytearray(pe_bytes()) + bytearray(1024)
        struct.pack_into('<I', raw, 408, 1536)
        struct.pack_into('<II', raw, 272, 0x1000, 40)
        struct.pack_into('<II', raw, 368, 0x1100, 64)
        struct.pack_into('<IIIII', raw, 512, 0x1080, 0, 0, 0x1040, 0x1080)
        dll = b'api-ms-win-core-synch-l1-2-0.dll\0'
        raw[576:576+len(dll)] = dll
        struct.pack_into('<QQQ', raw, 640, 0x10a0, 0x800000000000000c, 0)
        raw[674:688] = b'WaitOnAddress\0'
        struct.pack_into('<IIIIIIII', raw, 768, 1, 0x1140, 0, 0x1180, 0x1180, 0, 0, 0)
        dll = b'api-ms-win-crt-runtime-l1-1-0.dll\0'
        raw[832:832+len(dll)] = dll
        struct.pack_into('<QQ', raw, 896, 0x11b0, 0)
        raw[946:953] = b'malloc\0'
        self.dll.write_bytes(raw)
        self.assertEqual(read_imports(self.dll), [
            {'dll':'api-ms-win-core-synch-l1-2-0.dll','delay':False,'symbols':['WaitOnAddress',{'ordinal':12}]},
            {'dll':'api-ms-win-crt-runtime-l1-1-0.dll','delay':True,'symbols':['malloc']}])
        struct.pack_into('<I', raw, 272, 0x900000)
        self.dll.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'import directory'):
            read_imports(self.dll)

    def test_production_resolver_system32_only_exports_and_handle_cleanup(self):
        system = self.root/'Windows/System32'; system.mkdir(parents=True)
        for name in ('ucrtbase.dll','kernelbase.dll'): (system/name).write_bytes(b'system fixture')
        state = {'load':1, 'symbol':42, 'owner':2, 'foreign':False, 'freed':[]}
        def module_name(module, buffer, size):
            buffer.value = str((self.root if state['foreign'] else system) / ('ucrtbase.dll' if module==1 else 'kernelbase.dll'))
            return len(buffer.value)
        def get_owner(flags, address, output):
            self.assertEqual(flags, 6)
            ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = state['owner']
            return True
        def load(name, reserved, flags):
            self.assertEqual(flags, 0x800); return state['load']
        resolver = object.__new__(WindowsSystemResolver)
        resolver.system_directory = system
        resolver.kernel = SimpleNamespace(LoadLibraryExW=load, GetModuleFileNameW=module_name,
            GetProcAddress=lambda handle, symbol: state['symbol'], GetModuleHandleExW=get_owner,
            FreeLibrary=lambda handle: state['freed'].append(handle) or True)
        result = resolver('ucrtbase.dll', ['malloc', {'ordinal':12}])
        self.assertEqual(set(result['host_paths']), {str(system/'ucrtbase.dll'),str(system/'kernelbase.dll')})
        self.assertEqual(state['freed'], [1])
        state['symbol']=0
        with self.assertRaisesRegex(ValueError, 'symbol unavailable'): resolver('ucrtbase.dll',['missing'])
        self.assertEqual(state['freed'], [1,1])
        state['foreign']=True
        (self.root/'ucrtbase.dll').write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'outside Windows'): resolver('ucrtbase.dll',[])
        self.assertEqual(state['freed'], [1,1,1])
        state['load']=0
        with self.assertRaisesRegex(ValueError, 'contract unavailable'): resolver('ucrtbase.dll',[])
        with self.assertRaisesRegex(ValueError, 'Unreviewed'): resolver('unknown.dll',[])
        self.assertEqual(state['freed'], [1,1,1])

    def test_exact_used_symbols_and_ordinal_resolved_with_unused_contracts_recorded(self):
        imports = [{'dll': 'api-ms-win-crt-runtime-l1-1-0.dll', 'delay': False,
                    'symbols': ['malloc', {'ordinal': 12}]},
                   {'dll': 'Qt6Core.dll', 'delay': False, 'symbols': ['qt']},
                   {'dll': 'api-ms-win-core-synch-l1-2-0.dll', 'delay': True, 'symbols': ['WaitOnAddress']}]
        calls = []
        def resolve(name, symbols):
            calls.append((name, symbols))
            return {'dll': name, 'symbols': symbols, 'host_paths': ['C:\\Windows\\System32\\ucrtbase.dll']}
        report = verify_system_resolution([{'imports': imports}], resolve)
        self.assertEqual(len(calls), 44)
        self.assertEqual(dict(calls)['api-ms-win-crt-runtime-l1-1-0.dll'], ['malloc', {'ordinal': 12}])
        self.assertEqual(dict(calls)['api-ms-win-core-synch-l1-2-0.dll'], ['WaitOnAddress'])
        self.assertEqual(dict(calls)['api-ms-win-core-console-l1-1-0.dll'], [])
        self.assertEqual(len(report), 44)
        self.assertNotIn('Qt6Core.dll', dict(calls))
        def failed(name, symbols): raise ValueError('missing system symbol')
        with self.assertRaisesRegex(ValueError, 'missing system symbol'):
            verify_system_resolution([{'imports': imports}], failed)

    def test_actual_spec_filters_before_collect_and_keeps_resources_and_windowed_mode(self):
        calls = []
        class Analysis:
            def __init__(self, scripts, **kwargs):
                calls.append(('analysis', scripts, kwargs))
                self.pure=[];self.scripts=scripts;self.datas=kwargs['datas']
                self.binaries=[('ucrtbase.dll', str(self.dll_path), 'BINARY'), ('VCRUNTIME140.dll', '/vc.dll', 'BINARY')]
        Analysis.dll_path = self.dll
        def collect(exe, binaries, datas, **kwargs):
            calls.append(('collect', binaries, datas, kwargs))
        def exe(*args, **kwargs):
            self.assertTrue(kwargs['exclude_binaries']); self.assertFalse(kwargs['console']); return 'exe'
        source = Path(__file__).resolve().parents[1]
        with patch('windows_system_libraries.file_record', return_value={'bytes':7,'sha256':'a'*64}):
            runpy.run_path(str(source/'TwinQuay.spec'), init_globals={
                'SPECPATH': str(source), 'workpath': str(self.root), 'Analysis': Analysis,
                'PYZ': lambda x: 'pyz', 'EXE': exe, 'COLLECT': collect})
        self.assertEqual(calls[-1][1], [('VCRUNTIME140.dll','/vc.dll','BINARY')])
        self.assertIn(('build/notices', 'notices'), calls[0][2]['datas'])
        self.assertEqual(json.loads((self.root/'windows-system-exclusions.json').read_text())['excluded'][0]['name'], 'ucrtbase.dll')

if __name__ == '__main__': unittest.main()
