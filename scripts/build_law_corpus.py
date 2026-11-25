"""Build ALFRED's local law file from the official NCRB compilation of the Bharatiya Nyaya Sanhita, 2023 (owner 2026-11-26).

Usage: python -I scripts/build_law_corpus.py <BNS2023.pdf> [output.json]
Source: https://www.ncrb.mha.gov.in/uploads/SankalanPortal/DownloadPDF/BNS2023.pdf (NCRB, Ministry of Home Affairs; marked
"For Reference only"). Acts of Parliament may be reproduced (Copyright Act, 1957, s. 52(1)(q)). The PDF itself is not kept.
"""
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

SOURCE = "https://www.ncrb.mha.gov.in/uploads/SankalanPortal/DownloadPDF/BNS2023.pdf"
SECTIONS = 358
NUMBERED = re.compile(r"^\s*(\d{1,3})\.\s*(.*)$", re.S)
SENTENCE_END = re.compile(r"[.;:—–]\)?\s*$")
TITLE = re.compile(r"^(?:CHAPTER\b|Of [a-z])|^[^a-z]*[A-Z]{3}[^a-z]*$")  # a chapter or group title ("Of hurt"), not "Z."
BROKEN = re.compile(r"[.;:]\s+([A-Z][^.;:]*)$")  # "...State Government. Printing": a heading starts mid-line


def flat(text):
    return re.sub(r"(\w)- (\w)", r"\1-\2", " ".join(str(text or "").split()))  # "life- convict": a hyphen broken across lines


def table(pdf, first_text_page):
    """BNS section -> the repealed IPC entry, from the corresponding-section table."""
    rows = {}
    for page in pdf.pages(0, first_text_page):
        for found in page.find_tables().tables:
            for cells in found.extract():
                match = re.search(r"(?m)^\s*(\d{1,3})\.", cells[0] or "") if len(cells) >= 2 else None  # may follow a group title
                if match and 1 <= int(match[1]) <= SECTIONS and int(match[1]) not in rows:
                    ipc = re.search(r"(?ms)^\s*\d{1,3}[A-Z]{0,2}\..*", cells[1] or "")
                    rows[int(match[1])] = flat(ipc[0] if ipc else cells[1])
    return rows


def margin(text, start):
    """Where the lines printed above a section begin, and its chapter (if new) and margin heading. They follow the last
    line that ends a sentence; a wrapped heading, a chapter title and a group title ("Of hurt") have no sentence end."""
    lines, at = [], start
    while len(lines) < 20:  # a justified heading can print one word per line
        previous = text.rfind("\n", 0, at - 1) + 1
        line = text[previous:at].strip()
        if line and lines and SENTENCE_END.search(line) and not TITLE.search(line):
            break
        if line and lines and (broken := BROKEN.search(line)):
            lines.insert(0, broken[1]); at = previous + text[previous:at].rindex(broken[1])
            break
        if line: lines.insert(0, line)
        at = previous
        if previous == 0: break
    chapter = " ".join(line for line in lines if TITLE.search(line) and not line.startswith("Of "))
    heading = " ".join(line for line in lines if not TITLE.search(line))
    return at, flat(chapter), re.sub(r"^Chapters and Sections\s+", "", flat(heading)).rstrip(". ")


def loose(tables, number, heading):
    """The IPC entries of a table row split by sub-section ("318. Cheating. / 318 (1) / 415. Cheating."), which
    find_tables misses: the last row that starts with this BNS number and heading, up to the next BNS row."""
    rows = list(re.finditer(rf"(?m)^\s*{number}\.\s*{re.escape(heading[:20])}", tables))
    if not rows:
        return ""
    after = re.search(rf"(?m)^\s*{number + 1}\.\s", tables[rows[-1].end():])
    span = tables[rows[-1].end():rows[-1].end() + (after.start() if after else 400)]
    return flat(" ".join(m[0] for m in re.finditer(r"(?m)^\s*\d{1,3}[A-Z]{0,2}\.\s.*$", span)))


def build(path):
    raw = Path(path).read_bytes()
    pdf = fitz.open(stream=raw, filetype="pdf")
    first = next(i for i in range(pdf.page_count) if "This Act may be called the Bharatiya Nyaya Sanhita" in pdf[i].get_text())
    ipc = table(pdf, first)
    tables = "\n".join(pdf[i].get_text() for i in range(first))
    text = "\n".join(re.sub(r"(?m)^\s*(?:Index\s+)?HomePage\s*$|^\s*Index\s*$", "", pdf[i].get_text()) for i in range(first, pdf.page_count))
    text = re.split(r"—+\s*Note:\s*For Reference only", text)[0]
    starts, at = [], 0
    for number in range(1, SECTIONS + 1):
        found = re.compile(rf"(?m)^\s*{number}\.(?=\s|\()").search(text, at)  # "115.(1)" has no space
        if not found:
            raise SystemExit(f"Section {number} was not found after offset {at}.")
        starts.append(found.start()); at = found.end()
    margins = [margin(text, start) for start in starts]
    sections, chapter = [], ""
    for index, start in enumerate(starts):
        number = index + 1
        end = margins[index + 1][0] if index + 1 < len(starts) else len(text)
        chapter = margins[index][1] or chapter
        heading = margins[index][2]
        sections.append({"section": number, "chapter": chapter, "heading": heading,
                         "text": re.sub(rf"^{number}\.\s*", "", flat(text[start:end])), "ipc": ipc.get(number) or loose(tables, number, heading)})
    return {"act": "Bharatiya Nyaya Sanhita, 2023 (Act No. 45 of 2023)", "in_force_from": "2024-07-01",
            "repealed": "Indian Penal Code, 1860 (for offences committed before 1 July 2024)",
            "source": SOURCE, "source_note": "NCRB compilation, marked 'For Reference only'", "sha256": hashlib.sha256(raw).hexdigest(),
            "retrieved": date.today().isoformat(), "sections": sections}


def main():
    corpus = build(sys.argv[1])
    missing = [item["section"] for item in corpus["sections"] if not item["heading"] or len(item["text"]) < 20]
    assert len(corpus["sections"]) == SECTIONS and not missing, missing
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "apps/ml_engine/data/bns_2023.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(corpus['sections'])} sections; wrote {out}")


if __name__ == "__main__":
    main()
