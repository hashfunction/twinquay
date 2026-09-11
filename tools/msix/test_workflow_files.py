# Copyright 2026 Trieflow LLC. MIT.
"""Real fixture/receipt checks. These are not installed UI acceptance."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
from core.cleanup_plan import CleanupCandidate, CleanupPlan, EvidenceKind, timestamp
from core.quarantine import execute_plan, restore_receipt
from uuid import uuid4

from workflow_files import prepare, verify_plan, verify_receipt, COLLISION_BYTES


class WorkflowFilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="twinquay-workflow-test-")
        self.root = Path(self.temp.name).resolve()
        self.fixture = prepare(self.root)
        self.reference = self.root / "input/keep-original.bin"
        self.duplicate = self.root / "input/duplicate-copy.bin"
        self.plan = CleanupPlan(
            1,
            str(uuid4()),
            timestamp(),
            (CleanupCandidate.capture(self.duplicate, self.reference, EvidenceKind.EXACT_CONTENT),),
        )
        self.plan_path = self.root / "selected-plan.json"
        self.plan_path.write_text(json.dumps(self.plan.to_dict()))

    def tearDown(self):
        self.temp.cleanup()

    def test_real_domain_receipts_and_restored_bytes_are_independently_verified(self):
        verified = verify_plan(self.root)
        self.assertEqual(verified["candidate_count"], 1)
        receipt = execute_plan(self.plan, self.root / "quarantine")
        self.assertEqual(verify_receipt(self.root, "quarantined")["status"], "quarantined")
        self.duplicate.write_bytes(COLLISION_BYTES)
        restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
        self.assertEqual(verify_receipt(self.root, "restore_collision")["status"], "restore_collision")
        self.duplicate.unlink()
        restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
        self.assertEqual(verify_receipt(self.root, "restored")["status"], "restored")

    def test_plan_rejects_wrong_reference_similarity_extra_candidate_and_false_size(self):
        original = self.plan.to_dict()
        for field, value in (
            ("reference_path", str(self.root / "input/unique-control.bin")),
            ("path", str(self.root / "outside.bin")),
            ("evidence", "similarity"),
            ("candidate_size", True),
            ("reference_size", 9),
        ):
            changed = copy.deepcopy(original)
            changed["candidates"][0][field] = value
            self.plan_path.write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_plan(self.root)
        original["candidates"] *= 2
        self.plan_path.write_text(json.dumps(original))
        with self.assertRaises(ValueError):
            verify_plan(self.root)

    def test_receipt_cannot_claim_success_with_changed_reference_or_payload(self):
        receipt = execute_plan(self.plan, self.root / "quarantine")
        original = self.reference.read_bytes()
        self.reference.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify_receipt(self.root, "quarantined")
        self.reference.write_bytes(original)
        payload = receipt.receipt_path.parent / "payload" / receipt.items[0].item_id / receipt.items[0].name
        payload.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify_receipt(self.root, "quarantined")

    def test_equal_bytes_reference_replacement_is_not_original_preservation(self):
        execute_plan(self.plan, self.root / "quarantine")
        previous = self.reference.read_bytes()
        self.reference.rename(self.root / "original-retained-by-test.bin")
        self.reference.write_bytes(previous)
        with self.assertRaisesRegex(ValueError, "filesystem identity"):
            verify_receipt(self.root, "quarantined")

    def test_receipt_rejects_other_plan_extra_items_and_premature_status(self):
        receipt = execute_plan(self.plan, self.root / "quarantine")
        original = json.loads(receipt.receipt_path.read_text())
        for mutation in ("plan", "items", "status"):
            changed = copy.deepcopy(original)
            if mutation == "plan":
                changed["plan"]["plan_id"] = str(uuid4())
            if mutation == "items":
                changed["items"] *= 2
            if mutation == "status":
                changed["items"][0]["status"] = "moving"
            receipt.receipt_path.write_text(json.dumps(changed))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify_receipt(self.root, "quarantined")

    def test_prepare_evidence_contains_no_encoded_fixture_bytes(self):
        self.assertNotIn("collision_base64", self.fixture)
        self.assertEqual(self.fixture["collision"]["bytes"], len(COLLISION_BYTES))
        self.assertEqual(set(self.fixture["collision"]), {"bytes", "sha256"})

    def test_exact_durable_files_required_after_quarantine_conflict_and_restore(self):
        receipt = execute_plan(self.plan, self.root / "quarantine")
        lock = receipt.receipt_path.parent / ".lock"
        extra = receipt.receipt_path.parent / "unexpected.bin"
        for status in ("quarantined", "restore_collision", "restored"):
            if status == "restore_collision":
                self.duplicate.write_bytes(COLLISION_BYTES)
                restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
            elif status == "restored":
                self.duplicate.unlink()  # This test owns its generated collision.
                restore_receipt(receipt.receipt_path, [receipt.items[0].item_id])
            with self.subTest(status=status):
                self.assertTrue(lock.is_file())
                self.assertEqual(verify_receipt(self.root, status)["status"], status)
                extra.write_bytes(b"unexpected durable file")
                with self.assertRaises(ValueError):
                    verify_receipt(self.root, status)
                extra.unlink()
                lock.unlink()
                with self.assertRaisesRegex(ValueError, "durable quarantine"):
                    verify_receipt(self.root, status)
                # The next real restore acquires/recreates its own durable lock;
                # no test write repairs the evidence on behalf of the product.

    def test_prepare_never_reuses_existing_fixture(self):
        original = self.reference.read_bytes()
        with self.assertRaises((ValueError, FileExistsError)):
            prepare(self.root)
        self.assertEqual(self.reference.read_bytes(), original)

    def test_symlink_substitutions_and_extra_input_are_rejected(self):
        self.duplicate.unlink()
        self.duplicate.symlink_to(self.reference)
        with self.assertRaises(ValueError):
            verify_plan(self.root)
        self.duplicate.unlink()
        self.duplicate.write_bytes(self.reference.read_bytes())
        (self.root / "input/unexpected.bin").write_bytes(b"unowned")
        with self.assertRaises(ValueError):
            verify_plan(self.root)


if __name__ == "__main__":
    unittest.main()
