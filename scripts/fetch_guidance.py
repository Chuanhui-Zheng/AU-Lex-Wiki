"""Fetch Fair Work Ombudsman guidance pages and downloadable guides."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from config import config

ROOT = "https://www.fairwork.gov.au"
def catalogue() -> list[dict]:
    manifest = json.loads(Path(config.worklaw_source_manifest).read_text())
    fwo = manifest["fair_work_ombudsman"]
    pages = {
        "workplace_guides": fwo["guides_index"],
        "fact_sheets": fwo["fact_sheets_index"],
        "best_practice_guides": fwo["best_practice_guides_index"],
    }
    records = {}
    for source_type, index_url in pages.items():
        response = httpx.get(index_url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            title = " ".join(link.get_text(" ", strip=True).split())
            href = urljoin(ROOT, link["href"])
            if not title:
                continue
            is_download = href.lower().endswith(".docx") and source_type == "workplace_guides"
            is_page = href.startswith(ROOT + "/tools-and-resources/" + source_type.replace("_", "-"))
            if not (is_download or is_page):
                continue
            if href.lower().endswith(".pdf"):
                continue
            key = (source_type, href)
            records[key] = {
                "source_type": source_type,
                "title": title,
                "url": href,
                "format": "docx" if is_download else "html",
            }
    return sorted(records.values(), key=lambda item: (item["source_type"], item["title"], item["url"]))


def safe_id(record: dict) -> str:
    text = record["source_type"] + "-" + record["title"]
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:120]


def fetch(record: dict, raw_dir: Path) -> dict:
    item_id = safe_id(record)
    suffix = ".docx" if record["format"] == "docx" else ".html"
    target = raw_dir / f"{item_id}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size < 100:
        response = httpx.get(record["url"], timeout=90, follow_redirects=True)
        response.raise_for_status()
        target.write_bytes(response.content)
    return {
        **record,
        "id": item_id,
        "path": str(target),
        "publisher": "Fair Work Ombudsman",
        "document_type": "guidance",
        "authority_level": "official_guidance",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    raw_dir = Path(config.data_dir) / "raw" / "guidance"
    records = [fetch(record, raw_dir) for record in catalogue()]
    output = Path(config.data_dir) / "guidance_index.json"
    output.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    print(f"Fetched {len(records)} official FWO guidance records")


if __name__ == "__main__":
    main()
