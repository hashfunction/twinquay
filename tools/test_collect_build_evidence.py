# Copyright 2026 Trieflow LLC. MIT.
"""Production TOC/native-origin collector fixtures; no Windows acceptance claim."""
import ast
import json
import importlib.util
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from collect_build_evidence import ANALYSIS_FIELDS, VERSION_FIELDS, SIGNATURE_FIELDS, collect, metadata_request, validate_metadata, write_evidence
from msix.msix_qualification import file_record, inventory_tree


def pe_bytes():
    data = bytearray(1024)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<HHI", data, 132, 0x8664, 1, 1234)
    struct.pack_into("<H", data, 148, 240)  # PE32+ optional header
    struct.pack_into("<H", data, 152, 0x20b)
    struct.pack_into("<Q", data, 176, 0x140000000)
    struct.pack_into("<II", data, 184, 4096, 512)
    struct.pack_into("<II", data, 208, 8192, 512)
    struct.pack_into("<I", data, 260, 16)
    data[392:400] = b'.rdata\0\0'
    struct.pack_into("<IIII", data, 400, 512, 4096, 512, 512)
    return bytes(data)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / "build/DupliSift"
        self.work.mkdir(parents=True)
        self.stage = self.root / "dist/DupliSift"
        (self.stage / "_internal/notices").mkdir(parents=True)
        self.original = self.root / "native-input.dll"
        self.original.write_bytes(pe_bytes())
        (self.stage / "_internal/vendor-runtime.dll").write_bytes(pe_bytes())
        (self.stage / "DupliSift.exe").write_bytes(pe_bytes())
        self.notices = self.root / "build/notices/dependency-inventory.json"
        self.notices.parent.mkdir()
        self.notices.write_text('[{"name":"Python","version":"3.12.10","notices":[]}]\n')
        (self.stage / "_internal/notices/dependency-inventory.json").write_bytes(self.notices.read_bytes())
        self.analysis = ([], [], [], [], {}, [], [], False, {}, 0, [], [], "3.12.10", [],
                         [("qt.app", str(self.root / "qt/app.py"), "PYMODULE")],
                         [("vendor-runtime.dll", str(self.original), "BINARY")], [], [], [], [])
        self.collected = [("DupliSift.exe", str(self.original), "EXECUTABLE"),
                          ("vendor-runtime.dll", str(self.original), "BINARY")]
        self.write_tocs()
        self.inventory = self.root / "package-inventory.json"
        self.refresh_inventory()
        from windows_system_libraries import filter_binaries, MINIMUM_WINDOWS
        _, exclusions = filter_binaries(self.analysis[15], MINIMUM_WINDOWS)
        (self.work / 'windows-system-exclusions.json').write_text(json.dumps(exclusions))

    def write_tocs(self):
        for name, value in {
            "Analysis-00.toc": self.analysis,
            "PYZ-00.toc": (str(self.work / "PYZ-00.pyz"), self.analysis[14]),
            "COLLECT-00.toc": (self.collected,),
        }.items():
            (self.work / name).write_text(repr(value), encoding="utf-8")
        # EXE contains a version-resource constructor in real PyInstaller. It
        # must be retained as raw evidence, never evaluated as executable code.
        (self.work / "EXE-00.toc").write_text("(VSVersionInfo(ffi=FixedFileInfo()),)")

    def refresh_inventory(self):
        self.inventory.write_text(json.dumps({"sourceCommit": "a" * 40, "files": inventory_tree(self.stage)}))

    def collect(self):
        return collect(self.work, self.stage, self.notices, self.inventory, "6.22.2", "a" * 40)

    def test_real_pinned_toc_shapes_native_origin_hashes_and_raw_notices(self):
        evidence, outputs = self.collect()
        self.assertEqual(len(evidence["native_files"]), 2)
        self.assertEqual(evidence["native_files"][1]["original_path"], str(self.original))
        self.assertEqual(evidence["native_files"][1]["pe"]["machine"], "0x8664")
        self.assertEqual(evidence["native_files"][1]["original_sha256"], file_record(self.original)["sha256"])
        self.assertEqual(outputs["dependency-inventory.json"], self.notices.read_bytes())
        self.assertIn(b"VSVersionInfo", outputs["pyinstaller-EXE-00.toc.txt"])
        frozen = json.loads(outputs["frozen-build-tocs.json"])
        self.assertEqual(frozen["pyz_modules"][0]["name"], "qt.app")
        self.assertFalse(evidence["license_clearance"])
        self.assertFalse(evidence["corresponding_source_published"])

    def test_missing_unknown_duplicate_and_unsafe_native_origins_fail(self):
        for name in ("../vendor-runtime.dll", "C:\\vendor-runtime.dll", "a:stream.dll", "vendor-runtime.dll."):
            with self.subTest(name=name):
                self.collected[1] = (name, str(self.original), "BINARY")
                self.write_tocs()
                with self.assertRaises(ValueError):
                    self.collect()
        self.collected = [("DupliSift.exe", str(self.original), "EXECUTABLE")]
        self.write_tocs()
        with self.assertRaisesRegex(ValueError, "COLLECT native paths"):
            self.collect()
        self.collected += [("vendor-runtime.dll", str(self.original), "BINARY")] * 2
        self.write_tocs()
        with self.assertRaisesRegex(ValueError, "Duplicate COLLECT"):
            self.collect()
        self.collected.pop()
        self.collected[1] = ("vendor-runtime.dll", str(self.original), "SYMLINK")
        self.write_tocs()
        with self.assertRaisesRegex(ValueError, "Unknown native COLLECT type"):
            self.collect()

    def test_stage_inventory_origin_bytes_and_dependency_inventory_must_match(self):
        (self.stage / "_internal/vendor-runtime.dll").write_bytes(pe_bytes() + b"transformed")
        with self.assertRaisesRegex(ValueError, "stage inventory"):
            self.collect()
        self.refresh_inventory()
        with self.assertRaisesRegex(ValueError, "original/staged bytes"):
            self.collect()
        (self.stage / "_internal/vendor-runtime.dll").write_bytes(pe_bytes())
        self.refresh_inventory()
        self.notices.write_text("[]")
        with self.assertRaisesRegex(ValueError, "dependency inventory"):
            self.collect()

    def test_toc_is_literal_only_and_schema_version_is_pinned(self):
        marker = self.root / "executed"
        (self.work / "COLLECT-00.toc").write_text(f"__import__('pathlib').Path({str(marker)!r}).touch()")
        with self.assertRaisesRegex(ValueError, "literal TOC"):
            self.collect()
        self.assertFalse(marker.exists())
        self.write_tocs()
        with self.assertRaisesRegex(ValueError, "PyInstaller"):
            collect(self.work, self.stage, self.notices, self.inventory, "6.99", "a" * 40)
        (self.work / "Analysis-00.toc").write_text("([],)")
        with self.assertRaisesRegex(ValueError, "Analysis"):
            self.collect()

    def test_missing_original_and_invalid_pe_fail(self):
        self.original.write_bytes(b"not PE")
        for path in (self.stage / "DupliSift.exe", self.stage / "_internal/vendor-runtime.dll"):
            path.write_bytes(b"not PE")
        self.refresh_inventory()
        with self.assertRaisesRegex(ValueError, "PE"):
            self.collect()
        self.original.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.collect()

    def test_exclusions_rederived_from_real_analysis_bytes_and_never_staged(self):
        from windows_system_libraries import filter_binaries, MINIMUM_WINDOWS
        dll = self.root/'ucrtbase.dll'; dll.write_bytes(pe_bytes())
        analysis = list(self.analysis)
        analysis[15] = list(analysis[15]) + [('ucrtbase.dll',str(dll),'BINARY')]
        self.analysis = tuple(analysis); self.write_tocs()
        exclusion_path = self.work/'windows-system-exclusions.json'
        _, excluded = filter_binaries(self.analysis[15], MINIMUM_WINDOWS)
        exclusion_path.write_text(json.dumps(excluded))
        evidence, outputs = self.collect()
        self.assertEqual(len(evidence['native_files']), 2)
        self.assertEqual(evidence['excluded_native_files'][0]['original_path'], str(dll))
        self.assertIn(str(dll), [r['path'] for r in metadata_request(evidence)['files']])
        self.assertEqual(json.loads(outputs['frozen-build-tocs.json'])['analysis']['binaries'][-1][0], 'ucrtbase.dll')
        excluded['excluded'] = []
        exclusion_path.write_text(json.dumps(excluded))
        with self.assertRaisesRegex(ValueError, 'exclusion record differs'): self.collect()
        _, excluded = filter_binaries(self.analysis[15], MINIMUM_WINDOWS)
        exclusion_path.write_text(json.dumps(excluded))
        (self.stage/'_internal/ucrtbase.dll').write_bytes(dll.read_bytes())
        self.collected.append(('ucrtbase.dll',str(dll),'BINARY')); self.write_tocs(); self.refresh_inventory()
        with self.assertRaisesRegex(ValueError, 'OS component remained'): self.collect()

    def test_metadata_is_exact_complete_and_byte_bound(self):
        evidence, _ = self.collect()
        request = metadata_request(evidence)
        self.assertEqual(len(request["files"]), 3)  # original is deduplicated
        response = {"schema_version": 1, "platform": "Windows", "files": [
            dict(row, version=dict.fromkeys(VERSION_FIELDS), authenticode=dict(dict.fromkeys(SIGNATURE_FIELDS), status="Valid", signature_type="Catalog"))
            for row in request["files"]]}
        validate_metadata(request, response)
        for mutation in ("missing", "duplicate", "changed-hash", "other-platform", "missing-signature", "missing-version-field"):
            bad = json.loads(json.dumps(response))
            if mutation == "missing": bad["files"].pop()
            if mutation == "duplicate": bad["files"].append(bad["files"][0])
            if mutation == "changed-hash": bad["files"][0]["sha256"] = "b" * 64
            if mutation == "other-platform": bad["platform"] = "Linux"
            if mutation == "missing-signature": del bad["files"][0]["authenticode"]
            if mutation == "missing-version-field": del bad["files"][0]["version"]["original_filename"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_metadata(request, bad)

    def test_output_is_exclusive_and_validated_before_writing(self):
        dest = self.root / "evidence"
        dest.mkdir()
        (dest / "existing.json").write_text("retained")
        with self.assertRaises(FileExistsError):
            write_evidence(dest, {"new.json": b"{}", "existing.json": b"{}"})
        self.assertFalse((dest / "new.json").exists())
        self.assertEqual((dest / "existing.json").read_text(), "retained")

    def test_schemas_match_actual_installed_pyinstaller_classes(self):
        spec = importlib.util.find_spec("PyInstaller")
        if spec is None:
            self.skipTest("Actual installed PyInstaller schema comparison runs in the pinned build venv")
        root = Path(spec.origin).parent
        for filename, name, fields in (
            ("build_main.py", "Analysis", ANALYSIS_FIELDS),
            ("api.py", "PYZ", ("name", "toc")),
            ("api.py", "COLLECT", ("toc",)),
        ):
            tree = ast.parse((root / "building" / filename).read_text(encoding="utf-8"))
            cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
            guts = next(node.value for node in cls.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "_GUTS" for target in node.targets))
            self.assertEqual(tuple(item.elts[0].value for item in guts.elts), fields)

    def test_production_packager_stops_on_failed_provenance_before_nsis(self):
        if importlib.util.find_spec("PyInstaller") is None or importlib.util.find_spec("distro") is None:
            self.skipTest("Production packager test runs in the pinned build venv")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import package
        import PyInstaller.__main__
        import subprocess

        (self.root / "win_version_info.temp").write_text("{0}.{1}.{2}.{3}")
        previous = Path.cwd()
        calls = []

        def run(arguments, *, check):
            self.assertTrue(check)
            calls.append(arguments[1])
            if arguments[1] == "tools/collect_build_evidence.py":
                raise subprocess.CalledProcessError(1, arguments)

        try:
            os.chdir(self.root)
            with patch.object(package.sys, "platform", "win32"), patch.object(package.platform, "architecture", return_value=("64bit", "")), \
                    patch.object(package, "check_loc_doc", return_value=True), patch.object(package, "get_module_version", return_value="7.0.0"), \
                    patch.object(PyInstaller.__main__, "run"), patch.object(package.subprocess, "run", side_effect=run), \
                    patch.object(package.shutil, "which") as compiler:
                with self.assertRaises(subprocess.CalledProcessError):
                    package.package_windows()
                compiler.assert_not_called()
            self.assertEqual(calls, ["tools/collect_notices.py", "tools/package_inventory.py", "tools/collect_build_evidence.py"])
            self.assertFalse((self.root / "win_version_info.txt").exists())
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
