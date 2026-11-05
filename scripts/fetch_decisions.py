"""Fetch the curated Fair Work Commission decision set for V4."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from tqdm import tqdm

from config import config


def fetch_one(record: dict, raw_dir: Path) -> dict:
    suffix = ".html" if record["url"].lower().endswith((".htm", ".html")) else ".pdf"
    target = raw_dir / f"{record['id']}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size < 1000:
        response = httpx.get(record["url"], timeout=120, follow_redirects=True)
        response.raise_for_status()
        target.write_bytes(response.content)
    return {
        **record,
        "path": str(target),
        "publisher": "Fair Work Commission",
        "document_type": "decision",
        "authority_level": "decision",
    }


def main() -> None:
    records = json.loads(Path("config/decisions_v4.json").read_text())
    raw_dir = Path(config.data_dir) / "raw" / "decisions"
    output, failures = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_one, record, raw_dir): record for record in records}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching FWC decisions"):
            try:
                output.append(future.result())
            except Exception as exc:
                failures.append({"record": futures[future], "error": str(exc)})
    output.sort(key=lambda item: item["decision_date"])
    Path(config.data_dir).mkdir(parents=True, exist_ok=True)
    (Path(config.data_dir) / "decisions_index.json").write_text(json.dumps(output, indent=2))
    if failures:
        (Path(config.data_dir) / "decisions_failed.json").write_text(json.dumps(failures, indent=2))
    print(f"Fetched {len(output)} FWC decisions; failures={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
