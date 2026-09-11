param([switch]$SkipPackage)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $IsWindows -and $env:OS -ne 'Windows_NT') { throw 'Requires Windows x64 and Python 3.12.' }
function Run-Python { & .\.venv\Scripts\python.exe @args; if ($LASTEXITCODE -ne 0) { throw "Python command failed: $args" } }
if (Test-Path .venv) { throw 'Clean build requires no existing .venv; use a fresh checkout.' }
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 venv failed.' }
Run-Python -m pip install --require-hashes -r tools/python-windows-lock.txt
Run-Python -c 'import sys, struct; assert sys.version_info[:2] == (3,12); assert struct.calcsize("P") == 8'
Run-Python tools/msix/test_msix_qualification.py -v
New-Item -ItemType Directory -Force build-evidence | Out-Null
Run-Python build.py --clean
Run-Python tools/probe-windows-filesystem.py
Run-Python -m pytest core hscommon -q --junitxml=build-evidence/tests.xml
Run-Python -m pytest qt/tests -q --junitxml=build-evidence/qt-tests.xml
Run-Python tools/smoke-qt.py
Run-Python -m pip freeze | Out-File -Encoding utf8 build-evidence/python-freeze.txt
if (-not $SkipPackage) { Run-Python package.py --skip-nsis }
