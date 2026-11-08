"""Fetch current Modern Awards and Fair Work Ombudsman Pay Guides.

The official FWO award index is used as the catalogue. Award pages are saved
as HTML, while the linked DOCX Pay Guides are saved for deterministic parsing.
This adapter is deliberately limited to current awards; historical variation
material is retained from the Award page's History blocks for V2.
"""
import json
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import config

CODE_RE = re.compile(r"\bMA\d{6}\b", re.I)


def award_catalogue() -> list[dict]:
    manifest = json.loads(Path(config.worklaw_source_manifest).read_text())
    awards_index = manifest["fair_work_ombudsman"]["awards_index"]
    response = httpx.get(awards_index, timeout=60, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    seen = set()
    awards = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = CODE_RE.search(href + " " + link.get_text(" ", strip=True))
        if not match or "awards.fairwork.gov.au" not in href:
            continue
        code = match.group(0).upper()
        if code in seen:
            continue
        seen.add(code)
        awards.append({
            "code": code,
            "name": link.get_text(" ", strip=True),
            "url": href,
        })
    return sorted(awards, key=lambda item: item["code"])


def fetch_one(award: dict, raw_dir: Path) -> dict:
    code = award["code"]
    html_path = raw_dir / "awards" / f"{code}.html"
    guide_path = raw_dir / "pay_guides" / f"{code}.docx"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.parent.mkdir(parents=True, exist_ok=True)

    if not html_path.exists() or html_path.stat().st_size < 5000:
        response = httpx.get(award["url"], timeout=90, follow_redirects=True)
        response.raise_for_status()
        html_path.write_bytes(response.content)

    # The public pay-guide page is a JavaScript redirect.  Calling the
    # underlying official download endpoint directly gives us the DOCX bytes
    # and keeps the source deterministic for offline parsing.
    guide_url = (
        "https://calculate.fairwork.gov.au/Download/AwardSummary"
        f"?awardCode={code.lower()}&effectiveDate=&fileType=docx&krn="
    )
    guide_status = "missing"
    if not guide_path.exists():
        response = httpx.get(guide_url, timeout=90, follow_redirects=True)
        if response.status_code == 200 and response.content[:2] == b"PK":
            guide_path.write_bytes(response.content)
            guide_status = "downloaded"
    else:
        guide_status = "cached"

    return {
        "code": code,
        "name": award["name"],
        "award_url": award["url"],
        "html_path": str(html_path),
        "pay_guide_url": guide_url,
        "pay_guide_path": str(guide_path) if guide_path.exists() else "",
        "pay_guide_status": guide_status,
        "publisher": "Fair Work Ombudsman / Fair Work Commission",
        "document_type": "award",
        "authority_level": "instrument",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    raw_dir = Path(config.data_dir) / "raw"
    catalogue = award_catalogue()
    print(f"Found {len(catalogue)} current Modern Awards")
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_one, award, raw_dir): award for award in catalogue}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching Modern Awards"):
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({"award": futures[future], "error": str(exc)})

    results.sort(key=lambda item: item["code"])
    (Path(config.data_dir) / "awards_index.json").write_text(json.dumps(results, indent=2))
    if failures:
        (Path(config.data_dir) / "awards_failed.json").write_text(json.dumps(failures, indent=2))
    print(f"Downloaded {len(results)} awards; failures={len(failures)}")


if __name__ == "__main__":
    main()
