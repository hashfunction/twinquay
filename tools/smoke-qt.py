"""Offscreen startup/native/image decoder smoke; does not replace interactive Windows QA."""

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QtGui import QImage  # noqa: E402
from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR, qVersion  # noqa: E402
from core.pe import _block, _cache  # noqa: E402, F401
from qt.pe import _block_qt  # noqa: E402
from qt import dg_rc  # noqa: E402, F401

app = QApplication([])
image = QImage(16, 16, QImage.Format_RGB888)
image.fill(0x336699)
assert len(_block_qt.getblocks(image, 4)) == 16
print(f"Qt runtime {qVersion()} (bindings compiled against {QT_VERSION_STR}); PyQt {PYQT_VERSION_STR}; all 3 native extensions imported")
