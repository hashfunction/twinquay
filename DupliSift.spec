# Copyright 2026 Trieflow LLC. MIT.
# Reviewed Windows-only onedir recipe; application resources match package.py.
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(SPECPATH) / 'tools'))
from windows_system_libraries import filter_binaries
from msix.msix_qualification import QUALIFICATION_IDENTITY, STORE_IDENTITY

if QUALIFICATION_IDENTITY['minVersion'] != STORE_IDENTITY['minVersion']:
    raise ValueError('Both installed modes must share the reviewed Windows minimum')
a = Analysis(['run.py'], pathex=[], binaries=[], datas=[
    ('images/duplisift', 'images/duplisift'), ('build/locale', 'locale'),
    ('build/help', 'help'), ('LICENSE', '.'), ('THIRD-PARTY-NOTICES.txt', '.'),
    ('build/notices', 'notices'),
], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
# Analysis-00.toc remains untouched as evidence of the original dependency graph.
a.binaries, system_exclusions = filter_binaries(a.binaries, QUALIFICATION_IDENTITY['minVersion'])
with (Path(workpath) / 'windows-system-exclusions.json').open('x', encoding='utf-8') as stream:
    json.dump(system_exclusions, stream, indent=2)
    stream.write('\n')
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DupliSift', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None,
          icon=['images/duplisift/logo.ico'], version='win_version_info.txt')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name='DupliSift')
