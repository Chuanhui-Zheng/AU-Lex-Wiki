"""
Parse Federal Register XHTML documents into provision chunks for ingestion.

The HTML uses CSS classes to indicate structure:
  ActHead2  → Part heading
  ActHead3  → Division heading
  ActHead4  → Subdivision heading
  ActHead5  → Provision heading (number + title)
  subsection/subsection2 → Provision/subprovision body text
  paragraph → Paragraph text
  Definition → Definition text
  Penalty    → Penalty provision
"""
import re
import json
import warnings
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from tqdm import tqdm
from config import config

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

DATA = Path(config.data_dir)
CHUNKS = DATA / "chunks"
CHUNKS.mkdir(parents=True, exist_ok=True)

# CSS classes that indicate section heading level
SECTION_HEAD_CLASSES = {"ActHead5", "TOC5"}
# Body text classes
BODY_CLASSES = {
    "subsection", "subsection2", "paragraph", "paragraphsub", "paragraphsub-sub",
    "Definition", "Penalty", "SOText", "SOPara", "notetext", "notepara",
    "Tabletext", "Tablea", "TableHeading",
}
# Structural heading classes (Part/Division/Subdivision)
STRUCT_HEAD_CLASSES = {"ActHead2", "ActHead3", "ActHead4"}

SEC_NO_RE = re.compile(r"^(\d+[A-Z]*(?:[A-Z]{2})?(?:\.\d+)?)(?:\s+|$)")


def clean_text(text: str) -> str:
    """Remove excess whitespace and non-breaking spaces."""
    text = text.replace("\xa0", " ").replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_html(html_bytes: bytes) -> list[dict]:
    """Parse legislation HTML into a list of section dicts."""
    soup = BeautifulSoup(html_bytes.decode("utf-8", errors="replace"), "lxml")

    sections = []
    current_part = ""
    current_division = ""
    current_subdivision = ""
    current_sec_no = ""
    current_sec_heading = ""
    current_body_lines = []
    current_anchor = ""

    def flush():
        nonlocal current_sec_no, current_sec_heading, current_body_lines, current_anchor
        if current_sec_no and current_body_lines:
            body = " ".join(current_body_lines).strip()
            if len(body) > 20:
                sections.append({
                    "sectionNo": current_sec_no,
                    "sectionHeading": current_sec_heading,
                    "body": body,
                    "partHeading": current_part,
                    "divisionHeading": current_division,
                    "subdivisionHeading": current_subdivision,
                    "anchor": current_anchor,
                    "depth": 1,
                })
        current_sec_no = ""
        current_sec_heading = ""
        current_body_lines = []
        current_anchor = ""

    for tag in soup.find_all("p"):
        cls_set = set(tag.get("class", []))
        text = clean_text(tag.get_text())
        if not text:
            continue

        # Collect anchor IDs for this element (for later cross-ref)
        anchor = ""
        for a in tag.find_all("a", id=True):
            anchor = a.get("id", "")
            break
        # Also check parent span for id
        for a in tag.find_all(id=True):
            anchor = anchor or a.get("id", "")

        # Structural heading (Part / Division / Subdivision)
        if cls_set & {"ActHead2"}:
            flush()
            current_part = text
            current_division = ""
            current_subdivision = ""
            continue
        if cls_set & {"ActHead3"}:
            flush()
            current_division = text
            current_subdivision = ""
            continue
        if cls_set & {"ActHead4"}:
            flush()
            current_subdivision = text
            continue

        # Section heading
        if cls_set & SECTION_HEAD_CLASSES:
            flush()
            # Extract section number from heading text
            m = SEC_NO_RE.match(text)
            if m:
                current_sec_no = m.group(1)
                current_sec_heading = text[m.end():].strip()
            else:
                current_sec_no = text
                current_sec_heading = ""
            current_anchor = anchor
            continue

        # Body text – append to current section
        if cls_set & BODY_CLASSES and current_sec_no:
            current_body_lines.append(text)
            continue

        # Fallback: plain paragraph under a section
        if current_sec_no and not cls_set - {"", None}:
            current_body_lines.append(text)

    flush()
    return sections


def process_file(html_path: Path, meta: dict) -> Path | None:
    """Parse one HTML file and write chunks JSONL."""
    out = CHUNKS / f"{meta['titleId']}.jsonl"
    if out.exists():
        return out

    html = html_path.read_bytes()
    sections = parse_html(html)
    if not sections:
        return None

    lines = []
    for s in sections:
        chunk = {
            "titleId": meta["titleId"],
            "actName": meta["titleName"],
            "documentId": meta["registerId"],
            "compilationDate": meta["compilationDate"],
            "sectionNo": s["sectionNo"],
            "sectionHeading": s["sectionHeading"],
            "parentNo": "",
            "depth": s["depth"],
            "body": s["body"],
            "eid": f"{meta['titleId']}#{s['sectionNo']}",
            "sourceUrl": f"https://www.legislation.gov.au/{meta['titleId']}/{meta['compilationDate']}/{meta['compilationDate']}/text/original/epub/OEBPS/document_1/document_1.html#{s['anchor']}",
        }
        lines.append(json.dumps(chunk))

    out.write_text("\n".join(lines))
    return out


def main():
    index_path = DATA / "index.json"
    if not index_path.exists():
        print("No index.json found. Run fetch_worklaw_sources.py first.")
        return

    index = json.loads(index_path.read_text())
    print(f"Parsing {len(index)} official workplace-law documents...")

    total_sections = 0
    for meta in tqdm(index, desc="Parsing HTML"):
        html_path = Path(meta["htmlPath"])
        if not html_path.exists():
            continue
        out = process_file(html_path, meta)
        if out:
            count = len(out.read_text().splitlines())
            total_sections += count

    print(f"\nDone. {total_sections:,} provisions across {len(index)} documents → {CHUNKS}")


if __name__ == "__main__":
    main()
