"""Parse Award HTML and Pay Guide DOCX files into ingestion chunks."""
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from tqdm import tqdm

from config import config

CHUNKS = Path(config.data_dir) / "chunks"
AWARDS = Path(config.data_dir) / "raw" / "awards"
PAY_GUIDES = Path(config.data_dir) / "raw" / "pay_guides"
NO_RE = re.compile(r"^(\d+(?:\.\d+)*(?:[A-Z])?)(?:\s+|$)")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def chunks_for_award(meta: dict) -> list[dict]:
    soup = BeautifulSoup((AWARDS / f"{meta['code']}.html").read_bytes(), "html.parser")
    output = []
    current = None
    ordinal = 0

    def flush() -> None:
        nonlocal current
        if current and len(current["body"]) > 30:
            output.append(current)
        current = None

    for tag in soup.find_all(["p", "table"]):
        text = clean(tag.get_text(" ", strip=True))
        if len(text) < 3:
            continue
        classes = set(tag.get("class", []))
        if tag.name == "p" and "Level1" in classes:
            flush()
            match = NO_RE.match(text)
            ordinal += 1
            number = match.group(1) if match else f"part-{ordinal}"
            heading = text[match.end():].strip() if match else text
            current = {"sectionNo": number, "sectionHeading": heading, "body": text}
            continue
        if tag.name == "p" and "History" in classes:
            flush()
            ordinal += 1
            current = {"sectionNo": f"history-{ordinal}", "sectionHeading": "Variation history", "body": text}
            flush()
            continue
        if current and (tag.name == "p" or "AMODTable" in classes or "Level" in " ".join(classes)):
            current["body"] += "\n" + text
        elif tag.name == "table" and "AMODTable" in classes:
            ordinal += 1
            output.append({"sectionNo": f"table-{ordinal}", "sectionHeading": "Award table", "body": text})
    flush()

    return [
        {
            "titleId": meta["code"],
            "actName": meta["name"],
            "documentId": f"award:{meta['code']}",
            "compilationDate": "2026-01-01",
            "sectionNo": item["sectionNo"],
            "sectionHeading": item["sectionHeading"],
            "parentNo": "",
            "depth": 1,
            "body": item["body"],
            "eid": f"{meta['code']}#{item['sectionNo']}",
            "sourceUrl": meta["award_url"],
            "documentType": "award",
            "authorityLevel": "instrument",
            "publisher": meta["publisher"],
        }
        for item in output
    ]


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        if text.strip():
            paragraphs.append(clean(text))
    return "\n".join(paragraphs)


def chunks_for_pay_guide(meta: dict) -> list[dict]:
    raw_path = meta.get("pay_guide_path")
    path = Path(raw_path) if raw_path else None
    if path is None or not path.is_file():
        return []
    text = docx_text(path)
    pieces = [text[i:i + 4500] for i in range(0, len(text), 4500)]
    return [
        {
            "titleId": f"PG-{meta['code']}",
            "actName": f"{meta['name']} — Pay Guide",
            "documentId": f"payguide:{meta['code']}",
            "compilationDate": "2026-01-01",
            "sectionNo": f"pay-guide-{i}",
            "sectionHeading": "Minimum rates and allowances",
            "parentNo": "",
            "depth": 1,
            "body": piece,
            "eid": f"PG-{meta['code']}#pay-guide-{i}",
            "sourceUrl": meta["pay_guide_url"],
            "documentType": "pay_guide",
            "authorityLevel": "official_guidance",
            "publisher": "Fair Work Ombudsman",
        }
        for i, piece in enumerate(pieces, 1) if piece.strip()
    ]


def main() -> None:
    index = json.loads((Path(config.data_dir) / "awards_index.json").read_text())
    CHUNKS.mkdir(parents=True, exist_ok=True)
    total = 0
    for meta in tqdm(index, desc="Parsing Awards and Pay Guides"):
        award_records = chunks_for_award(meta)
        guide_records = chunks_for_pay_guide(meta)
        (CHUNKS / f"award_{meta['code']}.jsonl").write_text(
            "\n".join(json.dumps(item) for item in award_records)
        )
        guide_path = CHUNKS / f"payguide_{meta['code']}.jsonl"
        guide_path.write_text("\n".join(json.dumps(item) for item in guide_records))
        total += len(award_records) + len(guide_records)
    print(f"Parsed {total:,} V2 chunks")


if __name__ == "__main__":
    main()
