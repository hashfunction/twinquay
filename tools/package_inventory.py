"""Record exact staged package bytes, including Qt DLLs/plugins, without certifying them."""

import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
if not (root / "TwinQuay.exe").is_file():
    raise SystemExit("Missing TwinQuay.exe in staged package")
files = []
for path in sorted(root.rglob("*")):
    if path.is_file():
        with path.open("rb") as stream:
            sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        files.append(dict(path=str(path.relative_to(root)), size=path.stat().st_size, sha256=sha256))
if not any(Path(item["path"]).name.lower() == "qwindows.dll" for item in files):
    raise SystemExit("Required Qt Windows platform plugin is absent")
dest = Path("build-evidence")
dest.mkdir(exist_ok=True)
(dest / "package-inventory.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
print(f"Inventoried {len(files)} staged files; interactive Windows launch and license review still required.")
