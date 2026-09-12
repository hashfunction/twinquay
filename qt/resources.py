# Copyright 2026 Trieflow LLC. GPL-3.0; see LICENSE.
"""Original image assets shared by source and the PyInstaller data directory."""

from pathlib import Path
from qt import platform

ASSETS = {
    "logo_se": "logo-32.png",
    "logo_se_big": "logo-128.png",
    "plus": "plus.svg",
    "minus": "minus.svg",
    "search_clear_13": "search_clear_13.svg",
    "exchange": "exchange.svg",
    "zoom_in": "zoom_in.svg",
    "zoom_out": "zoom_out.svg",
    "zoom_original": "zoom_original.svg",
    "zoom_best_fit": "zoom_best_fit.svg",
    "error": "error.svg",
}


def asset_path(alias):
    return str(Path(platform.BASE_PATH) / "images" / "duplisift" / ASSETS[alias])
