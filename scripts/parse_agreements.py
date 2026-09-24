"""Parse official FWC enterprise agreement PDFs into clause-oriented chunks."""
import json
import re
from pathlib import Path

from pypdf import PdfReader

from config import config

CHUNKS = Path(config.data_dir) / "chunks"
CLAUSE_RE = re.compile(r"^(?:clause\s+)?([A-Z]?\d+(?:\.\d+)*(?:\([a-z0-9ivx]+\))?)\s+", re.I)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(clean(page.extract_text() or "") for page in reader.pages)


def split_clauses(text: str, size: int = 4800) -> list[tuple[str, str, str]]:
    pieces: list[tuple[str, str, str]] = []
    current_no = "preamble"
    current_heading = "Agreement text"
    current = ""
    ordinal = 0

    def flush() -> None:
        nonlocal current
        if current.strip():
            pieces.append((current_no, current_heading, current.strip()))
        current = ""

    for raw in text.splitlines():
        line = clean(raw)
        if not line:
            continue
        match = CLAUSE_RE.match(line)
        if match and (len(line) < 220 or line[:1].isdigit()):
            if current and len(current) + len(line) + 1 > size:
                flush()
            if not current:
                current_no = match.group(1)
                current_heading = line[match.end():].strip() or "Agreement clause"
        elif current and len(current) + len(line) + 1 > size:
            flush()
            ordinal += 1
            current_no = f"chunk-{ordinal}"
            current_heading = "Agreement text"
        current = f"{current}\n{line}".strip()
    flush()
    return pieces


def make_chunks(record: dict) -> list[dict]:
    text = extract_text(Path(record["path"]))
    if len(text) < 1000:
        raise ValueError(f"agreement PDF has insufficient extractable text: {record['agreement_id']}")
    pieces = split_clauses(text)
    date = record.get("approval_date") or "1900-01-01"
    output = []
    for index, (number, heading, body) in enumerate(pieces, 1):
        output.append({
            "titleId": f"AG-{record['agreement_id']}",
            "actName": record["title"],
            "documentId": f"agreement:{record['agreement_id']}:v{record.get('version', 1)}",
            "compilationDate": date,
            "sectionNo": number or f"chunk-{index}",
            "sectionHeading": heading,
            "parentNo": "",
            "depth": 1,
            "body": body,
            "eid": f"AG-{record['agreement_id']}#{number or index}",
            "sourceUrl": record["url"],
            "documentType": "enterprise_agreement",
            "authorityLevel": "instrument",
            "publisher": record["publisher"],
            "agreementId": record["agreement_id"],
            "industry": record.get("industry", ""),
        })
    return output


def main() -> None:
    index_path = Path(config.data_dir) / "agreements_index.json"
    index = json.loads(index_path.read_text())
    CHUNKS.mkdir(parents=True, exist_ok=True)
    active = {f"agreement_{record['agreement_id'].lower()}.jsonl" for record in index}
    for stale in CHUNKS.glob("agreement_*.jsonl"):
        if stale.name not in active:
            stale.unlink()
    total = 0
    for record in index:
        chunks = make_chunks(record)
        (CHUNKS / f"agreement_{record['agreement_id'].lower()}.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in chunks)
        )
        total += len(chunks)
    print(f"Parsed {total:,} V5 agreement chunks")


if __name__ == "__main__":
    main()
