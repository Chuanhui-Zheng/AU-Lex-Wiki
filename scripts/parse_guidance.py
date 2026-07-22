"""Convert official FWO guidance HTML/DOCX sources into ingestion chunks."""
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from config import config

CHUNKS = Path(config.data_dir) / "chunks"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        text = clean("".join(node.text or "" for node in paragraph.findall(".//w:t", ns)))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    blocks = []
    for tag in root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = clean(tag.get_text(" ", strip=True))
        if text and len(text) > 2:
            blocks.append(text)
    return "\n".join(blocks)


def split_text(text: str, size: int = 4200) -> list[str]:
    paragraphs = [clean(part) for part in text.splitlines() if clean(part)]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > size:
            chunks.append(current)
            current = ""
        current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def make_chunks(record: dict) -> list[dict]:
    path = Path(record["path"])
    text = docx_text(path) if record["format"] == "docx" else html_text(path)
    output = []
    for index, body in enumerate(split_text(text), 1):
        output.append({
            "titleId": f"GUIDE-{record['id']}",
            "actName": record["title"],
            "documentId": f"guidance:{record['id']}",
            "compilationDate": record["retrieved_at"][:10],
            "sectionNo": f"guide-{index}",
            "sectionHeading": record["title"],
            "parentNo": "",
            "depth": 1,
            "body": body,
            "eid": f"GUIDE-{record['id']}#guide-{index}",
            "sourceUrl": record["url"],
            "documentType": record["document_type"],
            "authorityLevel": record["authority_level"],
            "publisher": record["publisher"],
        })
    return output


def main() -> None:
    index = json.loads((Path(config.data_dir) / "guidance_index.json").read_text())
    CHUNKS.mkdir(parents=True, exist_ok=True)
    active_files = {f"guidance_{record['id']}.jsonl" for record in index}
    for stale in CHUNKS.glob("guidance_*.jsonl"):
        if stale.name not in active_files:
            stale.unlink()
    total = 0
    for record in index:
        chunks = make_chunks(record)
        (CHUNKS / f"guidance_{record['id']}.jsonl").write_text(
            "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks)
        )
        total += len(chunks)
    print(f"Parsed {total:,} V3 guidance chunks")


if __name__ == "__main__":
    main()
