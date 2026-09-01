"""Fetch selected official Fair Work Commission enterprise agreements."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from tqdm import tqdm

from config import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/138 Safari/537.36",
    "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
}


def fetch_one(record: dict, raw_dir: Path) -> dict:
    target = raw_dir / f"{record['agreement_id'].lower()}.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size < 1000:
        response = httpx.get(record["url"], headers=HEADERS, timeout=120, follow_redirects=True)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"official source did not return a PDF: {record['url']}")
        target.write_bytes(response.content)
    if target.stat().st_size < 1000:
        raise ValueError(f"agreement source is unexpectedly small: {target}")
    return {**record, "path": str(target), "publisher": "Fair Work Commission", "document_type": "enterprise_agreement", "authority_level": "instrument"}


def main() -> None:
    records = json.loads(Path("config/agreements_v5.json").read_text())
    raw_dir = Path(config.data_dir) / "raw" / "agreements"
    output, failures = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_one, record, raw_dir): record for record in records}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching FWC agreements"):
            try:
                output.append(future.result())
            except Exception as exc:
                failures.append({"record": futures[future], "error": str(exc)})
    output.sort(key=lambda item: item["agreement_id"])
    Path(config.data_dir).mkdir(parents=True, exist_ok=True)
    (Path(config.data_dir) / "agreements_index.json").write_text(json.dumps(output, indent=2))
    if failures:
        (Path(config.data_dir) / "agreements_failed.json").write_text(json.dumps(failures, indent=2))
    print(f"Fetched {len(output)} V5 agreements; failures={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
