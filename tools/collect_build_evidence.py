# Copyright 2026 Trieflow LLC. MIT.
"""Retain actual freezer inputs and native collector origins; no license clearance.

TOC schemas below are PyInstaller 6.22.2's building/{api,build_main}.py _GUTS.
EXE TOCs can contain VSVersionInfo constructors: retain these raw, never eval.
"""
import argparse
import ast
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path, PureWindowsPath
import struct
import subprocess
import sys
import tempfile

from msix.msix_qualification import file_record, inventory_tree
from windows_system_libraries import (SYSTEM_LIBRARIES, MINIMUM_WINDOWS, filter_binaries, read_imports,
                                      WindowsSystemResolver, verify_system_resolution)

PINNED_PYINSTALLER = "6.22.2"
NATIVE_SUFFIXES = {".exe", ".dll", ".pyd"}
VERSION_FIELDS = {"file_version", "product_version", "original_filename", "internal_name", "company_name",
                  "product_name", "file_description", "legal_copyright", "legal_trademarks", "language"}
SIGNATURE_FIELDS = {"status", "status_message", "signature_type", "is_os_binary", "signer_certificate", "timestamp_certificate"}
ANALYSIS_FIELDS = ("inputs", "pathex", "hiddenimports", "hookspath", "hooksconfig", "excludes",
                   "custom_runtime_hooks", "noarchive", "module_collection_mode", "optimize",
                   "_input_binaries", "_input_datas", "_python_version", "scripts", "pure",
                   "binaries", "zipfiles", "zipped_data", "datas", "_modules_outside_pyz")


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def literal_toc(raw, name, length):
    try:
        value = ast.literal_eval(raw.decode("utf-8"))
    except (ValueError, SyntaxError, UnicodeError, RecursionError) as exc:
        raise ValueError(f"Invalid literal TOC: {name}") from exc
    if not isinstance(value, tuple) or len(value) != length:
        raise ValueError(f"Unexpected PyInstaller {name} schema")
    return value


def entries(value, label):
    if not isinstance(value, list):
        raise ValueError(f"Expected {label} TOC list")
    result = []
    for item in value:
        if (not isinstance(item, tuple) or len(item) != 3 or not isinstance(item[0], str)
                or not item[0] or not isinstance(item[1], (str, type(None))) or not isinstance(item[2], str)):
            raise ValueError(f"Invalid {label} TOC entry")
        result.append(dict(name=item[0], source=item[1], typecode=item[2]))
    return result


def destination(name):
    path = PureWindowsPath(name)
    if (path.is_absolute() or path.drive or path.root or not path.parts or
            any(part in (".", "..") or part.endswith((" ", ".")) or ":" in part for part in path.parts)):
        raise ValueError(f"Unsafe COLLECT destination: {name}")
    return path.as_posix()


def pe_header(path):
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError(f"Not a PE image: {path}")
        offset = struct.unpack_from("<I", header, 60)[0]
        if offset < 64 or offset > 1024 * 1024:
            raise ValueError(f"Invalid PE header offset: {path}")
        stream.seek(offset)
        header = stream.read(24)
    if len(header) != 24 or header[:4] != b"PE\0\0":
        raise ValueError(f"Invalid PE signature: {path}")
    machine, sections, timestamp = struct.unpack_from("<HHI", header, 4)
    return dict(machine=f"0x{machine:04x}", sections=sections, coff_timestamp=timestamp)


def collect(work, stage, notices, inventory_path, pyinstaller_version, source_commit):
    if pyinstaller_version != PINNED_PYINSTALLER:
        raise ValueError("PyInstaller TOC schema version differs from audited 6.22.2")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8-sig"))
    actual = inventory_tree(stage)
    if inventory.get("sourceCommit") != source_commit or inventory.get("files") != actual:
        raise ValueError("Current source/stage inventory differs from the package input record")
    if file_record(notices) != file_record(stage / "_internal/notices/dependency-inventory.json"):
        raise ValueError("Collected dependency inventory differs from staged inventory")
    outputs = {"dependency-inventory.json": notices.read_bytes()}
    raw_tocs = {}
    toc_records = {}
    for path in sorted(work.glob("*.toc")):
        record = file_record(path)
        if record["bytes"] > 16 * 1024 * 1024 or len(raw_tocs) >= 32:
            raise ValueError("PyInstaller TOC evidence exceeds bound")
        raw = path.read_bytes()
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("PyInstaller TOC evidence exceeds bound")
        record = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        raw_tocs[path.name] = raw
        output_name = f"pyinstaller-{path.name}.txt"
        outputs[output_name] = raw
        toc_records[path.name] = dict(record, retained_file=output_name)
    required = {"Analysis-00.toc", "PYZ-00.toc", "COLLECT-00.toc"}
    if not required <= raw_tocs.keys():
        raise ValueError("Missing required actual PyInstaller TOCs")
    analysis = dict(zip(ANALYSIS_FIELDS, literal_toc(raw_tocs["Analysis-00.toc"], "Analysis", 20)))
    pyz = literal_toc(raw_tocs["PYZ-00.toc"], "PYZ", 2)
    collected = entries(literal_toc(raw_tocs["COLLECT-00.toc"], "COLLECT", 1)[0], "COLLECT")
    pyz_modules = entries(pyz[1], "PYZ")
    if len({row["name"] for row in pyz_modules}) != len(pyz_modules):
        raise ValueError("Duplicate frozen PYZ module")
    native = {}
    seen = set()
    for row in collected:
        name = destination(row["name"])
        staged_name = name if row["typecode"] in ("EXECUTABLE", "PKG") else f"_internal/{name}"
        if staged_name.casefold() in seen:
            raise ValueError(f"Duplicate COLLECT destination: {staged_name}")
        seen.add(staged_name.casefold())
        if Path(name).suffix.lower() not in NATIVE_SUFFIXES:
            continue
        if row["typecode"] not in ("EXECUTABLE", "EXTENSION", "BINARY", "DATA"):
            raise ValueError(f"Unknown native COLLECT type: {row['typecode']}")
        original = Path(row["source"] or "")
        if not original.is_absolute():
            raise ValueError(f"Native COLLECT source is not absolute: {original}")
        original_record = file_record(original)
        if actual.get(staged_name) != original_record:
            raise ValueError(f"COLLECT original/staged bytes differ: {staged_name}")
        native[staged_name] = dict(staged_path=staged_name, staged_absolute_path=str((stage / staged_name).absolute()),
                                   original_path=str(original), typecode=row["typecode"],
                                   original_sha256=original_record["sha256"], bytes=original_record["bytes"],
                                   pe=pe_header(original), imports=read_imports(original))
    expected = {name for name in actual if Path(name).suffix.lower() in NATIVE_SUFFIXES}
    if not expected or set(native) != expected:
        raise ValueError(f"COLLECT native paths differ from actual staged native inventory: {sorted(expected ^ set(native))}")
    # Independently rederive the exact exclusions from the saved, unmodified Analysis.
    exclusion_path = work / "windows-system-exclusions.json"
    exclusions = json.loads(exclusion_path.read_text(encoding="utf-8"))
    _, expected_exclusions = filter_binaries(analysis["binaries"], MINIMUM_WINDOWS)
    if exclusions != expected_exclusions:
        raise ValueError("System exclusion record differs from actual Analysis/original bytes")
    if any(PureWindowsPath(name).name.lower() in SYSTEM_LIBRARIES for name in actual):
        raise ValueError("Windows OS component remained in the distributable stage")
    excluded_native = []
    for row in exclusions["excluded"]:
        original = Path(row["source"])
        excluded_native.append(dict(name=row["name"], original_path=row["source"],
                                    original_sha256=row["sha256"], bytes=row["bytes"],
                                    pe=pe_header(original), imports=read_imports(original)))
    outputs["windows-system-exclusions.json"] = exclusion_path.read_bytes()
    inputs = dict(package_inventory=file_record(inventory_path), dependency_inventory=file_record(notices), tocs=toc_records,
                  system_exclusions=file_record(exclusion_path))
    frozen = dict(schema_version=1, source_commit=source_commit, pyinstaller_version=pyinstaller_version,
                  inputs=inputs, analysis=analysis, pyz_modules=pyz_modules, collect_entries=collected,
                  scope="Actual saved freezer TOCs; build analysis includes modules that may not be in PYZ")
    outputs["frozen-build-tocs.json"] = json_bytes(frozen)
    evidence = dict(schema_version=1, source_commit=source_commit, pyinstaller_version=pyinstaller_version,
                    inputs=inputs, native_files=[native[name] for name in sorted(native)],
                    scope="Byte-matched actual native collector origins; redistributability and corresponding source require audit",
                    excluded_native_files=excluded_native,
                    license_clearance=False, corresponding_source_published=False)
    return evidence, outputs


def metadata_request(evidence):
    files = {}
    for row in evidence["native_files"] + evidence.get("excluded_native_files", []):
        for name in ("original_path", "staged_absolute_path"):
            if name not in row:
                continue
            path = row[name]
            key = path.casefold()
            if key in files and files[key]["sha256"] != row["original_sha256"]:
                raise ValueError("Conflicting native metadata input bytes")
            files[key] = dict(path=path, sha256=row["original_sha256"])
    return dict(schema_version=1, files=list(files.values()))


def validate_metadata(request, response):
    if response.get("schema_version") != 1 or response.get("platform") != "Windows":
        raise ValueError("Invalid native metadata platform/schema")
    expected = {row["path"].casefold(): row["sha256"] for row in request["files"]}
    observed = {}
    for row in response.get("files", []):
        key = row.get("path", "").casefold()
        if (key in observed or key not in expected or row.get("sha256") != expected[key]
                or not isinstance(row.get("version"), dict) or not isinstance(row.get("authenticode"), dict)
                or not VERSION_FIELDS <= row["version"].keys() or not SIGNATURE_FIELDS <= row["authenticode"].keys()
                or not row["authenticode"].get("status") or not row["authenticode"].get("signature_type")):
            raise ValueError("Native metadata is incomplete, duplicated, foreign or differs from requested bytes")
        observed[key] = row
    if observed.keys() != expected.keys():
        raise ValueError("Native metadata omitted requested files")


def write_evidence(directory, outputs):
    for name in outputs:
        if Path(name).name != name or (directory / name).exists():
            raise FileExistsError(f"Evidence destination is not new: {name}")
    directory.mkdir(exist_ok=True, parents=True)
    for name, raw in outputs.items():
        with (directory / name).open("xb") as stream:
            stream.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if sys.platform != "win32":
        raise RuntimeError("Actual native build metadata requires Windows")
    source = args.source_root.resolve(strict=True)
    commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    evidence, outputs = collect(source / "build/TwinQuay", source / "dist/TwinQuay",
                                source / "build/notices/dependency-inventory.json", source / "build-evidence/package-inventory.json",
                                version("PyInstaller"), commit)
    resolver = WindowsSystemResolver()
    resolution = verify_system_resolution(evidence["native_files"], resolver)
    evidence["windows_system_resolution"] = dict(minimum_windows=MINIMUM_WINDOWS,
        observed_windows_version=list(sys.getwindowsversion()[:3]), system_directory=str(resolver.system_directory),
        contracts=resolution, scope="Current Windows host only; no Windows 10 19041 execution claim")
    evidence["build_policy_inputs"] = {name: file_record(source / name) for name in
        ("package.py", "TwinQuay.spec", "tools/windows_system_libraries.py", "tools/collect_build_evidence.py",
         "tools/msix/msix_qualification.py", "tools/python-windows-lock.txt")}
    request = metadata_request(evidence)
    existing = {row["path"].casefold() for row in request["files"]}
    for path in sorted({path for row in resolution for path in row["host_paths"]}):
        if path.casefold() not in existing:
            request["files"].append(dict(path=path, sha256=file_record(Path(path))["sha256"]))
            existing.add(path.casefold())
    with tempfile.TemporaryDirectory(prefix="twinquay-native-metadata-") as temporary:
        request_path, output_path = Path(temporary) / "request.json", Path(temporary) / "response.json"
        request_path.write_bytes(json_bytes(request))
        subprocess.run(["pwsh", "-NoLogo", "-NoProfile", "-File", str(source / "tools/collect-native-metadata.ps1"),
                        "-InputPath", str(request_path), "-OutputPath", str(output_path)], check=True, timeout=180)
        metadata = json.loads(output_path.read_text(encoding="utf-8-sig"))
    validate_metadata(request, metadata)
    for row in request["files"]:
        if file_record(Path(row["path"]))["sha256"] != row["sha256"]:
            raise ValueError("Native metadata input changed after observation")
    evidence["windows_metadata"] = metadata
    evidence["build_environment"] = dict(python_version=sys.version, executable=sys.executable, base_prefix=sys.base_prefix,
        sdk={key: os.environ.get(key) for key in ("WindowsSdkDir", "WindowsSDKVersion", "VCToolsInstallDir", "VCToolsVersion", "UniversalCRTSdkDir", "UCRTVersion")})
    outputs["native-build-provenance.json"] = json_bytes(evidence)
    write_evidence(source / "build-evidence", outputs)
    print(f"Retained actual freezer TOCs, dependency inventory and {len(evidence['native_files'])} byte-matched native origins; license/source gates remain open.")


if __name__ == "__main__":
    main()
