# Copyright 2026 Trieflow LLC. MIT. External native-dialog test host, not an app mode.
"""Execute the two real product chooser methods in an owned Windows Qt window."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    if sys.platform != "win32":
        raise RuntimeError("This fixture requires the actual Windows native dialog platform")
    os.environ["QT_QPA_PLATFORM"] = "windows"
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from qt.directories_dialog import DirectoriesDialog
    from qt.cleanup_plan_dialog import CleanupPlanDialog

    root = Path(sys.argv[1]).resolve(strict=True)
    selected = []
    app = QApplication([])
    window = QMainWindow()
    window.setWindowTitle("DupliSift native chooser fixture")
    window.resize(640, 480)
    window.app = SimpleNamespace(
        prefs=SimpleNamespace(use_native_dialogs=True),
        model=SimpleNamespace(add_directory=selected.append),
    )
    window.recentFolders = SimpleNamespace(insertItem=lambda path: None)
    window.lastAddedFolder = str(root)
    window.selected_plan = lambda: SimpleNamespace(to_dict=lambda: {"native_chooser_fixture": True})

    def run():
        try:
            DirectoriesDialog.addFolderTriggered(window)
            if len(selected) != 1 or Path(selected[0]).resolve() != root / "selected + [folder]":
                raise RuntimeError("Real source folder chooser did not select the exact owned fixture")
            CleanupPlanDialog.save_plan(window)
            plan = root / "selected + [plan].json"
            if json.loads(plan.read_text(encoding="utf-8")) != {"native_chooser_fixture": True}:
                raise RuntimeError("Real source save chooser did not exclusively save the expected JSON")
            print(json.dumps({"selected": selected, "saved": str(plan), "source_methods_completed": 2}), flush=True)
            app.exit(0)
        except Exception as exc:
            print(str(exc), file=sys.stderr, flush=True)
            app.exit(1)

    window.show()
    QTimer.singleShot(100, run)
    QTimer.singleShot(45000, lambda: app.exit(3))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
