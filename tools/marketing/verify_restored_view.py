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
from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from core.cleanup_plan import CleanupCandidate,CleanupPlan,EvidenceKind
from core.quarantine import execute_plan,restore_receipt
from qt.quarantine_dialog import QuarantineDialog
import workflow_files as oracle

app=QApplication([])
def click_checkbox(dialog):
    rect=dialog.table.visualItemRect(dialog.table.item(0,0))
    QTest.mouseClick(dialog.table.viewport(),Qt.MouseButton.LeftButton,pos=QPoint(rect.left()+12,rect.center().y()))
    app.processEvents()

def keyboard_checkbox(dialog):
    dialog.table.setFocus()
    QTest.keyClick(dialog.table,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(dialog.table,Qt.Key.Key_Space)
    app.processEvents()

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory).resolve();fixture=oracle.prepare(root)
    original=root/'Project Documents/Cedar House Brief.txt'
    duplicate=root/'Project Documents/Cedar House Brief - emailed.txt'
    plan=CleanupPlan.create([CleanupCandidate.capture(duplicate,original,EvidenceKind.EXACT_CONTENT)])
    Path(fixture['plan_path']).write_text(json.dumps(plan.to_dict()))
    oracle.verify_plan(root)
    receipt=execute_plan(plan,Path(fixture['quarantine']))
    oracle.verify_receipt(root,'quarantined')
    # Positive control: the same ordinary checkbox click/key route acts on an
    # eligible original model item, so the inactive test cannot pass by no-op.
    eligible=QuarantineDialog(None,SimpleNamespace(model=SimpleNamespace(last_cleanup_receipt=receipt)))
    eligible.resize(1800,900);eligible.show();app.processEvents()
    click_checkbox(eligible)
    assert eligible.table.item(0,0).checkState()==Qt.CheckState.Checked
    keyboard_checkbox(eligible)
    assert eligible.table.item(0,0).checkState()==Qt.CheckState.Unchecked
    QTest.keyClick(eligible,Qt.Key.Key_Escape);app.processEvents()
    assert not eligible.isVisible()
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
    cell=dialog.table.item(0,0);click_checkbox(dialog)
    keyboard_checkbox(dialog)
    assert cell.checkState()==Qt.CheckState.Unchecked
    assert not cell.flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert 'receipt.json' in dialog.caption.text()
    QTest.keyClick(dialog,Qt.Key.Key_Escape);app.processEvents()
    assert not dialog.isVisible()
    assert oracle.verify_receipt(root,'restored')==before
print('PASS actual Qt restored receipt: one five-column row, original path/status, inactive selection, ordinary Escape dismissal, unchanged restored bytes.')
