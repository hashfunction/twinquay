"""Actual Qt/domain replay of the additional restored-receipt view (local test).

The Windows capture still observes the real installed UIA provider separately.
"""
# Copyright 2026 Trieflow LLC. MIT.
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path[:0]=[str(Path(__file__).resolve().parents[2]),str(Path(__file__).resolve().parents[1]/'msix')]
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from core.cleanup_plan import CleanupCandidate,CleanupPlan,EvidenceKind
from core.quarantine import execute_plan,restore_receipt
from qt.quarantine_dialog import QuarantineDialog
import workflow_files as oracle

app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory).resolve();fixture=oracle.prepare(root)
    original=root/'Project Documents/Cedar House Brief.txt'
    duplicate=root/'Project Documents/Cedar House Brief - emailed.txt'
    plan=CleanupPlan.create([CleanupCandidate.capture(duplicate,original,EvidenceKind.EXACT_CONTENT)])
    Path(fixture['plan_path']).write_text(json.dumps(plan.to_dict()))
    oracle.verify_plan(root)
    receipt=execute_plan(plan,Path(fixture['quarantine']))
    oracle.verify_receipt(root,'quarantined')
    duplicate.write_bytes(oracle.COLLISION_BYTES)
    restore_receipt(receipt.receipt_path,[receipt.items[0].item_id])
    oracle.verify_receipt(root,'restore_collision')
    duplicate.unlink()
    restore_receipt(receipt.receipt_path,[receipt.items[0].item_id])
    before=oracle.verify_receipt(root,'restored')
    dialog=QuarantineDialog(None,SimpleNamespace(model=SimpleNamespace(last_cleanup_receipt=receipt)))
    dialog.resize(1800,900);dialog.show();app.processEvents()
    assert dialog.table.rowCount()==1 and dialog.table.columnCount()==5
    assert dialog.table.item(0,1).text()==str(duplicate)
    assert dialog.table.item(0,3).text()=='restored'
    assert not dialog.table.item(0,0).flags() & Qt.ItemFlag.ItemIsEnabled
    assert 'receipt.json' in dialog.caption.text()
    dialog.close();app.processEvents()
    assert oracle.verify_receipt(root,'restored')==before
print('PASS actual Qt restored receipt: one five-column row, original path/status, disabled selection, unchanged restored bytes.')
