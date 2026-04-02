from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re

from pypdf import PdfReader


OBJECT_RE = re.compile(rb"(?m)^([0-9]+)\s+([0-9]+)\s+obj\s*(.*?)\s*endobj", re.S)
PAGE_RE = re.compile(rb"/Type\s*/Page\b")
PAGES_RE = re.compile(rb"/Type\s*/Pages\b")
CATALOG_RE = re.compile(rb"/Type\s*/Catalog\b")
PARENT_RE = re.compile(rb"/Parent\s+\d+\s+\d+\s+R")


@dataclass(frozen=True)
class RecoveredPdf:
    repaired_bytes: bytes
    page_count: int


def rebuild_orphaned_pdf(raw_bytes: bytes) -> RecoveredPdf | None:
    """Rebuild a structurally broken PDF that lost its catalog/xref sections.

    Some uploaded PDFs still contain valid page/content objects but are missing
    the page tree, trailer, or xref table. In that case we can synthesize the
    missing root objects and make the document readable again.
    """

    if not raw_bytes.startswith(b"%PDF"):
        return None

    if b"startxref" in raw_bytes and (b"/Root" in raw_bytes or CATALOG_RE.search(raw_bytes)):
        return None

    objects = []
    page_object_ids: list[int] = []
    max_object_id = 0

    for match in OBJECT_RE.finditer(raw_bytes):
        object_id = int(match.group(1))
        generation = int(match.group(2))
        body = match.group(3).strip()
        if not body:
            continue
        objects.append((object_id, generation, body))
        max_object_id = max(max_object_id, object_id)
        if PAGE_RE.search(body) and not PAGES_RE.search(body):
            page_object_ids.append(object_id)

    if len(objects) < 3 or not page_object_ids:
        return None

    if any(CATALOG_RE.search(body) for _, _, body in objects):
        return None

    pages_object_id = max_object_id + 1
    catalog_object_id = max_object_id + 2

    rebuilt_objects: dict[int, tuple[int, bytes]] = {}
    for object_id, generation, body in objects:
        if PAGE_RE.search(body) and not PAGES_RE.search(body):
            if PARENT_RE.search(body):
                body = PARENT_RE.sub(f"/Parent {pages_object_id} 0 R".encode(), body, count=1)
            else:
                body = body.rstrip(b">>") + f"\n/Parent {pages_object_id} 0 R\n>>".encode()
        rebuilt_objects[object_id] = (generation, body)

    kids = b" ".join(f"{object_id} 0 R".encode() for object_id in page_object_ids)
    rebuilt_objects[pages_object_id] = (
        0,
        f"<< /Type /Pages /Count {len(page_object_ids)} /Kids [ ".encode() + kids + b" ] >>",
    )
    rebuilt_objects[catalog_object_id] = (0, f"<< /Type /Catalog /Pages {pages_object_id} 0 R >>".encode())

    output = BytesIO()
    output.write(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    max_output_object_id = max(rebuilt_objects)

    for object_id in sorted(rebuilt_objects):
        offsets[object_id] = output.tell()
        generation, body = rebuilt_objects[object_id]
        output.write(f"{object_id} {generation} obj\n".encode())
        output.write(body)
        if not body.endswith(b"\n"):
            output.write(b"\n")
        output.write(b"endobj\n")

    xref_offset = output.tell()
    output.write(f"xref\n0 {max_output_object_id + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for object_id in range(1, max_output_object_id + 1):
        offset = offsets.get(object_id, 0)
        state = "n" if object_id in offsets else "f"
        output.write(f"{offset:010d} 00000 {state} \n".encode())

    output.write(
        (
            f"trailer\n<< /Size {max_output_object_id + 1} /Root {catalog_object_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    repaired_bytes = output.getvalue()

    try:
        page_count = len(PdfReader(BytesIO(repaired_bytes)).pages)
    except Exception:
        return None

    if page_count < 1:
        return None

    return RecoveredPdf(repaired_bytes=repaired_bytes, page_count=page_count)
