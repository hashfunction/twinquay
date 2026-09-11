"""Bind every PyInstaller stage byte and original notices/assets to this source.

This inventory is build provenance, not a dependency license-clearance claim.
"""

import json
from pathlib import Path
import subprocess
import sys

from msix.msix_qualification import create_input_inventory

source = Path(__file__).resolve().parents[1]
commit = subprocess.run(
    ["git", "-C", str(source), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
).stdout.strip()
record = create_input_inventory(Path(sys.argv[1]), source, commit)
dest = source / "build-evidence"
dest.mkdir(exist_ok=True)
with (dest / "package-inventory.json").open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(f'Inventoried {len(record["files"])} staged files; dependency-notice gates remain open.')
