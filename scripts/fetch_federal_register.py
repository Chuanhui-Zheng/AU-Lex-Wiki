"""
Fetch selected in-force legal documents from the Federal Register of Legislation.
Saves HTML content directly from /{titleId}/{date}/{date}/text/original/epub/OEBPS/
to data/raw/{titleId}.html. No EPUB download required.
"""
import json
import time
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from config import config

API = config.legislation_api_base
RAW = Path(config.data_dir) / "raw"
RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"Accept": "application/json"}
BASE_URL = "https://www.legislation.gov.au"


def get_all_titles(title_type: str = "act", max_principal: int = 300) -> list[dict]:
    """Fetch in-force titles, stopping once we have max_principal principal acts."""
    titles = []
    principal_count = 0
    skip = 0
    page_size = 500
    collection = _collection(title_type)

    while True:
        try:
            r = httpx.get(
                f"{API}/Titles",
                params={
                    "$filter": f"isInForce eq true and collection eq '{collection}'",
                    "$top": page_size,
                    "$skip": skip,
                },
                headers=HEADERS, timeout=30,
            )
            r.raise_for_status()
        except Exception as e:
            print(f"  Error fetching titles (skip={skip}): {e}")
            break
        batch = r.json().get("value", [])
        if not batch:
            break
        titles.extend(batch)
        principal_count += sum(1 for t in batch if t.get("isPrincipal"))
        skip += page_size
        time.sleep(0.2)
        if principal_count >= max_principal or len(batch) < page_size:
            break
    return titles


def _collection(title_type: str) -> str:
    return {
        "act": "Act",
        "legislative_instrument": "LegislativeInstrument",
    }.get(title_type, "Act")


def get_current_version(title_id: str) -> dict | None:
    """Get the current/latest compilation version for a title."""
    r = httpx.get(
        f"{API}/Versions",
        params={
            "$filter": f"titleId eq '{title_id}'",
            "$top": 20,
            "$orderby": "start desc",
        },
        headers=HEADERS, timeout=15,
    )
    if r.status_code != 200:
        return None
    items = r.json().get("value", [])
    # Prefer isCurrent, then isLatest, then first
    for v in items:
        if v.get("isCurrent") and v.get("registerId"):
            return v
    for v in items:
        if v.get("isLatest") and v.get("registerId"):
            return v
    for v in items:
        if v.get("registerId"):
            return v
    return None


def build_html_url(title_id: str, start_date: str) -> str:
    """Build URL for the EPUB HTML content."""
    d = start_date[:10]  # YYYY-MM-DD
    return f"{BASE_URL}/{title_id}/{d}/{d}/text/original/epub/OEBPS/document_1/document_1.html"


def fetch_html(title_id: str, start_date: str) -> bytes | None:
    """Fetch the full HTML text of an act."""
    url = build_html_url(title_id, start_date)
    try:
        r = httpx.get(url, timeout=60, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 500:
            return r.content
    except Exception as e:
        print(f"  Error fetching HTML for {title_id}: {e}")
    return None


def fetch_one_title(t: dict) -> tuple[dict | None, dict | None]:
    """Fetch one title; return (metadata, failure) for bounded parallelism."""
    tid = t["id"]
    dest = RAW / f"{tid}.html"
    meta_path = RAW / f"{tid}.json"

    if dest.exists() and dest.stat().st_size > 2000 and meta_path.exists():
        return json.loads(meta_path.read_text()), None

    last_reason = "download failed"
    for attempt in range(3):
        try:
            version = get_current_version(tid)
            if not version:
                last_reason = "no version"
                break
            start_date = version.get("start", "")
            if not start_date:
                last_reason = "no start date"
                break
            html = fetch_html(tid, start_date)
            if html:
                dest.write_bytes(html)
                meta = {
                    "titleId": tid,
                    "titleName": t.get("name", ""),
                    "registerId": version.get("registerId", ""),
                    "compilationDate": start_date[:10],
                    "compilationNumber": version.get("compilationNumber", ""),
                    "htmlPath": str(dest),
                    "year": t.get("year"),
                    "sizeBytes": len(html),
                }
                meta_path.write_text(json.dumps(meta))
                return meta, None
            last_reason = "download failed"
        except Exception as exc:
            last_reason = str(exc)
        time.sleep(0.5 * (attempt + 1))

    return None, {"titleId": tid, "name": t.get("name", ""), "reason": last_reason}


def main(max_principal: int = 300, workers: int = 6):
    """Fetch up to max_principal principal legal documents (default 300)."""
    print("Fetching Act titles...")
    acts = get_all_titles("act", max_principal=max_principal)
    print(f"Found {len(acts)} Acts")

    # Filter to principal acts (originating acts, not amending instruments)
    acts = [t for t in acts if t.get("isPrincipal", False)]
    print(f"Principal in-force Acts: {len(acts)}")

    index = []
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_one_title, title) for title in acts]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching legislation HTML"):
            meta, failure = future.result()
            if meta:
                index.append(meta)
            if failure:
                failed.append(failure)

    index.sort(key=lambda item: item.get("titleName", ""))

    index_path = Path(config.data_dir) / "index.json"
    index_path.write_text(json.dumps(index, indent=2))

    if failed:
        fail_path = Path(config.data_dir) / "failed.json"
        fail_path.write_text(json.dumps(failed, indent=2))
        print(f"\n{len(failed)} titles failed → {fail_path}")

    print(f"\nDone. {len(index)} acts saved → {index_path}")


if __name__ == "__main__":
    main()
