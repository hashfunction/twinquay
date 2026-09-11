"""Real file/ZIP/XML fixtures for packaging boundaries; no native/GUI claims.
Copyright 2026 Trieflow LLC. MIT, derived in part from PixelQuay's MIT tests.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

try:
    import msix_qualification as msix
except ImportError:
    msix = None


def digest(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(msix, "TwinQuay MSIX qualification is not implemented")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.release = self.root / "release"
        self.source = self.root / "source"
        self.artwork = Path(__file__).resolve().parents[2] / "images/twinquay/logo-256.png"
        self.commit = "a" * 40
        files = {
            "TwinQuay.exe": b"PyInstaller embedded bootloader output",
            "_internal/python312.dll": b"Python 3.12 runtime",
            "_internal/PyQt6/QtCore.pyd": b"PyQt6 binding",
            "_internal/PyQt6/Qt6/bin/Qt6Core.dll": b"Qt6 Core",
            "_internal/PyQt6/Qt6/bin/Qt6Gui.dll": b"Qt6 Gui",
            "_internal/PyQt6/Qt6/bin/Qt6Widgets.dll": b"Qt6 Widgets",
            "_internal/PyQt6/Qt6/plugins/platforms/qwindows.dll": b"Windows platform plugin",
            "_internal/core/pe/_block.pyd": b"local compiled extension",
            "_internal/LICENSE": b"GPL-3.0 source notice",
            "_internal/THIRD-PARTY-NOTICES.txt": b"third-party source notice",
            "_internal/notices/Python-LICENSE.txt": b"Python license",
            "_internal/notices/PyQt6/LICENSE": b"PyQt6 notice",
            "_internal/notices/Hardcoded-Software-BSD-3-Clause.txt": b"BSD notice",
            "_internal/help/index.html": b"original help",
            "_internal/locale/en/LC_MESSAGES/ui.mo": b"locale fixture",
        }
        for relative, data in files.items():
            path = self.release / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for relative in ("LICENSE", "THIRD-PARTY-NOTICES.txt"):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(files["_internal/" + relative])
        source_bsd = Path(__file__).resolve().parents[2] / "hscommon/LICENSE"
        (self.source / "hscommon").mkdir()
        (self.source / "hscommon/LICENSE").write_bytes(source_bsd.read_bytes())
        (self.release / "_internal/notices/Hardcoded-Software-BSD-3-Clause.txt").write_bytes(source_bsd.read_bytes())
        (self.release / "_internal/notices/THIRD-PARTY-NOTICES.txt").write_bytes(
            files["_internal/THIRD-PARTY-NOTICES.txt"]
        )
        for name in ("logo-32.png", "logo-256.png", "logo.ico"):
            data = (self.artwork.parent / name).read_bytes()
            for base in (self.source, self.release / "_internal"):
                path = base / "images/twinquay" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        for relative, data in [
            ("tools/python-windows-lock.txt", b"locked distributions"),
            ("qt/app.py", b'NAME = "TwinQuay"'),
        ]:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.notices = [
            dict(name="Python", version="3.12", notices=["Python-LICENSE.txt"], review="collected; audit required"),
            dict(name="PyQt6", version="6.11.0", notices=["PyQt6/LICENSE"], review="collected; audit required"),
            dict(name="unresolved-fixture", version="1.0", notices=[], review="required"),
        ]
        for name in ("PyInstaller", "PyQt6-Qt6", "PyQt6_sip"):
            notice = self.release / "_internal/notices" / name / "LICENSE"
            notice.parent.mkdir(parents=True)
            notice.write_bytes((name + " notice fixture").encode())
            self.notices.append(
                dict(name=name, version="1.0", notices=[name + "/LICENSE"], review="collected; audit required")
            )
        self.notice_path = self.release / "_internal/notices/dependency-inventory.json"
        self.notice_path.write_text(json.dumps(self.notices))
        self.inventory = self.root / "inventory.json"
        self.startup = self.root / "startup.json"
        self.refresh_evidence()

    def refresh_evidence(self):
        record = msix.create_input_inventory(self.release, self.source, self.commit)
        self.inventory.write_text(json.dumps(record))
        self.startup.write_text(
            json.dumps(
                dict(
                    source_commit=self.commit,
                    windows_native_startup=True,
                    window_title="TwinQuay",
                    executable_sha256=record["files"]["TwinQuay.exe"]["sha256"],
                    package_inventory_sha256=digest(self.inventory.read_bytes())["sha256"],
                    interactive_cleanup_restore_verified=False,
                    native_source_clearance=False,
                    msix_built=False,
                    submitted=False,
                )
            )
        )

    def stage(self):
        return msix.stage_release(
            self.release, self.artwork, self.root / "stage", self.commit, self.inventory, self.startup, self.source
        )

    def test_complete_stage_source_notices_and_receipt_binding(self):
        record = self.stage()
        self.assertEqual(record["releaseInput"], msix.inventory_tree(self.release))
        self.assertEqual(record["payload"], msix.inventory_tree(self.root / "stage"))
        self.assertEqual(record["sourceCommit"], self.commit)
        self.assertEqual(record["startupReceipt"]["sha256"], digest(self.startup.read_bytes())["sha256"])
        self.assertEqual(record["runtime"]["executable"], "TwinQuay.exe")
        self.assertIn("unresolved-fixture", record["unresolvedNotices"])
        self.assertFalse(record["licenseClearanceClaimed"])
        self.assertFalse(record["publicRelease"])
        self.assertIn("build output", record["buildProvenance"]["bootloader"])
        for name, size in [("StoreLogo.png", 50), ("Square44x44Logo.png", 44), ("Square150x150Logo.png", 150)]:
            self.assertEqual(msix.png_dimensions((self.root / "stage/Assets" / name).read_bytes()), (size, size))

    def test_inventory_or_stage_tampering_extra_and_omitted_files_rejected(self):
        for mode in ("changed", "extra", "missing"):
            with self.subTest(mode=mode):
                path = self.release / "_internal/help/index.html"
                original = path.read_bytes()
                extra = self.release / "unexpected.dll"
                if mode == "changed":
                    path.write_bytes(b"altered")
                if mode == "extra":
                    extra.write_bytes(b"undeclared")
                if mode == "missing":
                    path.unlink()
                with self.assertRaises(ValueError):
                    self.stage()
                path.write_bytes(original)
                extra.unlink(missing_ok=True)

    def test_changed_runtime_notices_or_original_images_rejected_even_with_fresh_inventory(self):
        for relative in (
            "_internal/LICENSE",
            "_internal/THIRD-PARTY-NOTICES.txt",
            "_internal/images/twinquay/logo-32.png",
        ):
            path = self.release / relative
            original = path.read_bytes()
            path.write_bytes(b"changed")
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                self.refresh_evidence()
            path.write_bytes(original)
        for relative in (
            "_internal/python312.dll",
            "_internal/PyQt6/QtCore.pyd",
            "_internal/PyQt6/Qt6/bin/Qt6Gui.dll",
            "_internal/PyQt6/Qt6/plugins/platforms/qwindows.dll",
            "_internal/notices/PyQt6/LICENSE",
        ):
            path = self.release / relative
            original = path.read_bytes()
            path.unlink()
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                self.refresh_evidence()
            path.write_bytes(original)

    def test_qt5_payload_rejected(self):
        (self.release / "_internal/Qt5Core.dll").write_bytes(b"retired runtime")
        with self.assertRaises(ValueError):
            self.refresh_evidence()

    def test_source_copied_notice_changes_rejected_before_receipts_can_be_refreshed(self):
        for relative in (
            "_internal/notices/Hardcoded-Software-BSD-3-Clause.txt",
            "_internal/notices/THIRD-PARTY-NOTICES.txt",
        ):
            path = self.release / relative
            original = path.read_bytes()
            with self.subTest(relative=relative):
                path.write_bytes(b"replaced third-party license text")
                with self.assertRaisesRegex(ValueError, "Original source notice"):
                    self.refresh_evidence()
            path.write_bytes(original)

    def test_missing_runtime_dependency_notice_entry_cannot_be_hidden_by_new_inventory(self):
        notices = [entry for entry in self.notices if entry["name"] != "PyQt6-Qt6"]
        self.notice_path.write_text(json.dumps(notices))
        with self.assertRaises(ValueError):
            self.refresh_evidence()

    def test_coherent_foreign_source_receipt_and_inventory_rejected(self):
        inventory = json.loads(self.inventory.read_text())
        inventory["sourceCommit"] = "b" * 40
        self.inventory.write_text(json.dumps(inventory))
        receipt = json.loads(self.startup.read_text())
        receipt["source_commit"] = "b" * 40
        receipt["package_inventory_sha256"] = digest(self.inventory.read_bytes())["sha256"]
        self.startup.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            self.stage()

    def test_changed_source_metadata_rejected(self):
        (self.source / "tools/python-windows-lock.txt").write_bytes(b"resolved different dependencies")
        with self.assertRaises(ValueError):
            self.stage()

    def test_actual_source_title_and_options_control_match_observer_contract(self):
        import ast

        source = Path(__file__).resolve().parents[2]
        title = ast.parse((source / "qt/app.py").read_text())
        values = [
            node.value.value
            for node in ast.walk(title)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and any(isinstance(n, ast.Name) and n.id == "NAME" for n in node.targets)
        ]
        self.assertEqual(values, ["TwinQuay"])
        tree = ast.parse((source / "qt/directories_dialog.py").read_text())
        button_titles = [
            node.args[0].args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "QPushButton"
            and node.args
            and isinstance(node.args[0], ast.Call)
            and node.args[0].args
            and isinstance(node.args[0].args[0], ast.Constant)
        ]
        self.assertEqual(button_titles.count("More Options"), 1)

    def test_changed_or_unproven_startup_receipt_rejected(self):
        original = json.loads(self.startup.read_text())
        for key, value in [
            ("source_commit", "b" * 40),
            ("executable_sha256", "f" * 64),
            ("package_inventory_sha256", "f" * 64),
            ("windows_native_startup", False),
            ("window_title", "TwinQuay error"),
        ]:
            receipt = copy.deepcopy(original)
            receipt[key] = value
            self.startup.write_text(json.dumps(receipt))
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.stage()

    def test_stage_and_build_output_never_overwrite_existing_directory(self):
        stage = self.root / "stage"
        stage.mkdir()
        marker = stage / "owner.txt"
        marker.write_text("preserve")
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual(marker.read_text(), "preserve")

    def test_directory_link_or_native_junction_is_not_followed(self):
        link = self.release / "redirect"
        target = self.root / "external"
        target.mkdir()
        if os.name == "nt":
            subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
        else:
            link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.stage()
        link.rmdir() if os.name == "nt" else link.unlink()

    def package(self):
        record = self.stage()
        path = self.root / "fixture.msix"
        with zipfile.ZipFile(path, "w") as archive:
            for relative in record["payload"]:
                archive.write(self.root / "stage" / relative, relative)
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("AppxBlockMap.xml", "<BlockMap/>")
        record["unpackedVerification"] = msix.verify_unpacked(self.root / "stage", record["payload"])
        return path, record

    def test_exact_container_and_unpacked_payload_match(self):
        package, record = self.package()
        self.assertEqual(msix.verify_msix(package, record["payload"])["verifiedPayloadFiles"], len(record["payload"]))
        self.assertEqual(
            msix.verify_unpacked(self.root / "stage", record["payload"])["verifiedPayloadFiles"], len(record["payload"])
        )

    def test_installed_inventory_allows_only_signature_metadata_beyond_payload(self):
        record = self.stage()
        stage = self.root / "stage"
        (stage / "AppxSignature.p7x").write_bytes(b"ephemeral signing metadata fixture")
        self.assertEqual(
            msix.verify_installed(stage, record["payload"])["verifiedPayloadFiles"], len(record["payload"])
        )
        (stage / "unexpected-resource.txt").write_bytes(b"unrecorded installed resource")
        with self.assertRaises(ValueError):
            msix.verify_installed(stage, record["payload"])

    def test_install_preflight_rejects_coherently_rehashed_package_record(self):
        package, record = self.package()
        record_path = self.root / "package-record.json"
        record["containerVerification"] = msix.verify_msix(package, record["payload"])
        record_path.write_text(json.dumps(record))
        self.assertTrue(
            msix.verify_record_inputs(
                package, record_path, self.release, self.artwork, self.commit, self.inventory, self.startup, self.source
            )
        )
        # An internally consistent hash/record cannot substitute another input revision.
        record["sourceCommit"] = "b" * 40
        record_path.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            msix.verify_record_inputs(
                package, record_path, self.release, self.artwork, self.commit, self.inventory, self.startup, self.source
            )
        record["sourceCommit"] = self.commit
        record["runtime"] = {}
        record_path.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            msix.verify_record_inputs(
                package, record_path, self.release, self.artwork, self.commit, self.inventory, self.startup, self.source
            )

    def test_opc_decodes_once_and_accepts_exact_bytes(self):
        package, record = self.package()
        for encoded, decoded in [
            ("libc%2B%2B.dll", "libc++.dll"),
            ("literal%2520.txt", "literal%20.txt"),
            ("R%C3%A9sum%C3%A9.txt", "Résumé.txt"),
        ]:
            data = b"fixture bytes"
            with zipfile.ZipFile(package, "a") as archive:
                archive.writestr(encoded, data)
            record["payload"][decoded] = digest(data)
        msix.verify_msix(package, record["payload"])

    def test_opc_alias_traversal_bad_utf8_and_special_paths_rejected(self):
        package, record = self.package()
        for name in (
            "%54winQuay.exe",
            "twinquay.EXE",
            "_internal%2fescape.dll",
            "_internal%5cescape.dll",
            "%2e%2e/escape",
            "/absolute",
            "C:evil",
            "x%FF",
            "x%GG",
            "x%00",
            "CON.txt",
            "name.",
            "empty//name",
        ):
            changed = self.root / "changed.msix"
            shutil.copyfile(package, changed)
            with zipfile.ZipFile(changed, "a") as archive:
                archive.writestr(name, b"extra")
            with self.subTest(name=name), self.assertRaises(ValueError):
                msix.verify_msix(changed, record["payload"])

    def test_zip_link_and_unexpected_empty_directory_rejected(self):
        package, record = self.package()
        for name, mode in [("redirect", 0o120777), ("unreviewed/", 0o40755)]:
            changed = self.root / "changed.msix"
            shutil.copyfile(package, changed)
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            with zipfile.ZipFile(changed, "a") as archive:
                archive.writestr(info, b"")
            with self.assertRaises(ValueError):
                msix.verify_msix(changed, record["payload"])

    def test_manifest_semantics_independent_of_coherent_hashes(self):
        package, record = self.package()
        for before, after in [
            (b"runFullTrust", b"internetClient"),
            (b"TwinQuay.exe", b"other.exe"),
            (b"CN=TwinQuay-CI-Qualification", b"CN=foreign"),
        ]:
            data = (self.root / "stage/AppxManifest.xml").read_bytes().replace(before, after)
            with self.assertRaises(ValueError):
                msix.validate_manifest(data)
        root = self.root / "stage"
        (root / "AppxManifest.xml").write_bytes(data)
        record["payload"]["AppxManifest.xml"] = digest(data)
        with self.assertRaises(ValueError):
            msix.verify_unpacked(root, record["payload"])

    def test_exact_sdk_semantic_pack_unpack_and_tool_integrity(self):
        sdk = self.root / "Windows Kits/10/bin/10.0.26100.0/x64"
        sdk.mkdir(parents=True)
        tool = sdk / "makeappx.exe"
        tool.write_bytes(b"fixture tool")
        commands = []

        def runner(command):
            commands.append(command)
            p = Path(command[command.index("/p") + 1])
            d = Path(command[command.index("/d") + 1])
            if command[1] == "pack":
                with zipfile.ZipFile(p, "w") as z:
                    for f in d.rglob("*"):
                        if f.is_file():
                            z.write(f, f.relative_to(d).as_posix())
                    z.writestr("[Content_Types].xml", "<Types/>")
                    z.writestr("AppxBlockMap.xml", "<BlockMap/>")
            else:
                with zipfile.ZipFile(p) as z:
                    z.extractall(d)

        output = self.root / "package-output"
        msix.build_qualification(
            self.release,
            self.artwork,
            self.commit,
            tool,
            "10.0.26100.0",
            output,
            self.inventory,
            self.startup,
            self.source,
            runner,
        )
        self.assertEqual([c[1] for c in commands], ["pack", "unpack"])
        self.assertNotIn("/nv", commands[0])
        self.assertNotIn("/o", commands[0])
        self.assertIn("/v", commands[0])
        record = json.loads((output / "package-record.json").read_text())
        self.assertFalse(record["signed"])
        self.assertFalse(record["installationQualificationPassed"])
        self.assertEqual(record["makeAppx"]["sha256"], digest(tool.read_bytes())["sha256"])
        with self.assertRaises(ValueError):
            msix._tool_record(tool, "10.0.22621.0")

    def test_sdk_tool_change_aborts_without_publishing_output(self):
        sdk = self.root / "Windows Kits/10/bin/10.0.26100.0/x64"
        sdk.mkdir(parents=True)
        tool = sdk / "makeappx.exe"
        tool.write_bytes(b"original SDK tool")

        def changing_tool(command):
            tool.write_bytes(b"changed SDK tool")

        output = self.root / "package-output"
        with self.assertRaisesRegex(ValueError, "MakeAppx changed"):
            msix.build_qualification(
                self.release,
                self.artwork,
                self.commit,
                tool,
                "10.0.26100.0",
                output,
                self.inventory,
                self.startup,
                self.source,
                changing_tool,
            )
        self.assertFalse(output.exists())

    def test_install_preflight_requires_exact_typed_unpack_evidence(self):
        package, record = self.package()
        record["containerVerification"] = msix.verify_msix(package, record["payload"])
        record_path = self.root / "package-record.json"
        count = len(record["payload"])
        for value in [
            None,
            {},
            {"verifiedPayloadFiles": 0},
            {"verifiedPayloadFiles": str(count)},
            {"verifiedPayloadFiles": float(count)},
            {"verifiedPayloadFiles": True},
            {"verifiedPayloadFiles": count, "unexpected": True},
        ]:
            with self.subTest(value=value):
                altered = copy.deepcopy(record)
                if value is None:
                    del altered["unpackedVerification"]
                else:
                    altered["unpackedVerification"] = value
                record_path.write_text(json.dumps(altered))
                with self.assertRaisesRegex(ValueError, "unpack"):
                    msix.verify_record_inputs(
                        package,
                        record_path,
                        self.release,
                        self.artwork,
                        self.commit,
                        self.inventory,
                        self.startup,
                        self.source,
                    )


if __name__ == "__main__":
    unittest.main()
