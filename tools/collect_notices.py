"""Collect installed dependency notices for review; missing license texts are reported."""

from importlib.metadata import distributions
import json
from pathlib import Path
import shutil
import sys

root = Path("build/notices")
if root.exists():
    shutil.rmtree(root)  # Generated output: do not carry retired dependencies into a new package.
root.mkdir(parents=True)
shutil.copyfile("hscommon/LICENSE", root / "Hardcoded-Software-BSD-3-Clause.txt")
python_notices = [
    Path(sys.base_prefix) / name for name in ("LICENSE.txt", "LICENSE", "Resources/English.lproj/License.rtf")
]
python_copied = []
for notice in python_notices:
    if notice.is_file():
        target = root / ("Python-" + notice.name)
        shutil.copyfile(notice, target)
        python_copied.append(target.name)
records = [
    dict(
        name="Python",
        version=sys.version,
        notices=python_copied,
        review="collected; audit required" if python_copied else "Python runtime license text required",
    )
]

for distribution in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = distribution.metadata["Name"]
    dest = root / name
    notices = [
        p
        for p in (distribution.files or [])
        if any(word in Path(p).name.lower() for word in ("license", "licence", "copying", "notice", "copyright"))
    ]
    copied = []
    for index, notice in enumerate(notices):
        source = Path(distribution.locate_file(notice))
        if source.is_file():
            dest.mkdir(exist_ok=True)
            output = dest / f"{index}-{source.name}"
            shutil.copyfile(source, output)
            copied.append(str(output.relative_to(root)))
    records.append(
        dict(
            name=name,
            version=distribution.version,
            license=distribution.metadata.get("License-Expression") or distribution.metadata.get("License"),
            notices=copied,
            review="required" if not copied else "collected; audit required",
        )
    )
(root / "dependency-inventory.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
shutil.copyfile("THIRD-PARTY-NOTICES.txt", root / "THIRD-PARTY-NOTICES.txt")
print(f"Collected notices for {len(records)} distributions; see dependency-inventory.json for unresolved texts.")
