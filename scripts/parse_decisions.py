"""Parse selected FWC decisions into clause-sized ingestion chunks."""
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from config import config

CHUNKS = Path(config.data_dir) / "chunks"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def extract_text(record: dict) -> str:
    path = Path(record["path"])
    if path.suffix == ".pdf":
        return "\n".join(clean(page.extract_text() or "") for page in PdfReader(str(path)).pages)
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return "\n".join(clean(text) for text in soup.stripped_strings if clean(text))


def split_text(text: str, size: int = 5200) -> list[str]:
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
    output = []
    for index, body in enumerate(split_text(extract_text(record)), 1):
        output.append({
            "titleId": f"DEC-{record['id']}",
            "actName": f"{record['case_name']} — {record['citation']}",
            "documentId": f"decision:{record['id']}",
            "compilationDate": record["decision_date"],
            "sectionNo": f"para-{index}",
            "sectionHeading": record["category"].replace("_", " ").title(),
            "parentNo": "",
            "depth": 1,
            "body": body,
            "eid": f"DEC-{record['id']}#para-{index}",
            "sourceUrl": record["url"],
            "documentType": record["document_type"],
            "authorityLevel": record["authority_level"],
            "publisher": record["publisher"],
            "decisionId": record["id"],
            "citation": record["citation"],
            "caseName": record["case_name"],
            "category": record["category"],
        })
    return output


def main() -> None:
    index = json.loads((Path(config.data_dir) / "decisions_index.json").read_text())
    CHUNKS.mkdir(parents=True, exist_ok=True)
    total = 0
    for record in index:
        chunks = make_chunks(record)
        (CHUNKS / f"decision_{record['id']}.jsonl").write_text(
            "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks)
        )
        total += len(chunks)
    print(f"Parsed {total:,} V4 decision chunks")


if __name__ == "__main__":
    main()
