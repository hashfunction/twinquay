"""Render original TwinQuay vector artwork; no upstream product marks are reused."""

from pathlib import Path
import struct
from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer

root = Path(__file__).resolve().parents[1] / "images" / "twinquay"
root.mkdir(exist_ok=True)
logo = """<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect width="256" height="256" rx="54" fill="#143642"/><path d="M48 178V78a30 30 0 0 1 60 0v100H88V78a10 10 0 0 0-20 0v100z" fill="#ffffff"/><path d="M148 178V78a30 30 0 0 1 60 0v100h-20V78a10 10 0 0 0-20 0v100z" fill="#67ddc2"/><path d="M40 196h176" stroke="#67ddc2" stroke-width="12" stroke-linecap="round"/></svg>"""
(root / "logo.svg").write_text(logo)
entries = []
for size in (16, 32, 48, 128, 256):
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(logo.encode())).render(painter)
    painter.end()
    filename = root / f"logo-{size}.png"
    assert image.save(str(filename), "PNG")
    entries.append((size, filename.read_bytes()))
header = struct.pack("<HHH", 0, 1, len(entries))
offset = 6 + 16 * len(entries)
directory = b""
for size, data in entries:
    directory += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
    offset += len(data)
(root / "logo.ico").write_bytes(header + directory + b"".join(data for _, data in entries))
shapes = {
    "plus": '<path d="M8 2v12M2 8h12"/>',
    "minus": '<path d="M2 8h12"/>',
    "search_clear_13": '<path d="m4 4 8 8M12 4l-8 8"/>',
    "exchange": '<path d="M2 5h12l-3-3m3 9H2l3 3"/>',
    "zoom_in": '<circle cx="7" cy="7" r="5"/><path d="m11 11 4 4M4 7h6M7 4v6"/>',
    "zoom_out": '<circle cx="7" cy="7" r="5"/><path d="m11 11 4 4M4 7h6"/>',
    "zoom_original": '<rect x="2" y="2" width="12" height="12"/><path d="M7 5h1v6"/>',
    "zoom_best_fit": '<path d="M2 6V2h4m4 0h4v4M2 10v4h4m4 0h4v-4"/>',
    "error": '<circle cx="8" cy="8" r="6"/><path d="M8 4v5m0 2v1"/>',
}
for name, shape in shapes.items():
    (root / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><g fill="none" stroke="#607987" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{shape}</g></svg>'
    )
