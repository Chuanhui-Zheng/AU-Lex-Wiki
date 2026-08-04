"""Fetch the curated official source set for AU-WorkLaw-Atlas.

V1 downloads the Fair Work Act from the Federal Register and records the
official FWC/FWO indexes as source manifests for the next ingestion stages.
It deliberately does not bulk-download agreements or decisions.
"""
import json
from pathlib import Path

from config import config
from scripts.fetch_federal_register import fetch_one_title, get_current_version


def main() -> None:
    manifest_path = Path(config.worklaw_source_manifest)
    manifest = json.loads(manifest_path.read_text())
    data_dir = Path(config.data_dir)
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Keep the V1 fetch deterministic: only the core federal workplace statute
    # is downloaded automatically. Other official sources remain explicit,
    # auditable entry points until their document-specific parsers are enabled.
    title_ids = set(manifest["federal_register"].get("title_ids", []))
    requested_names = manifest["federal_register"].get("title_names", [])
    index = []
    titles = []
    for title_id in sorted(title_ids):
        titles.append({"id": title_id, "name": "Fair Work Act 2009", "isPrincipal": True})

    # Resolve additional named instruments through the official Register API.
    # This keeps the manifest readable while allowing Regulation identifiers to
    # change independently of the repository.
    for title_name in requested_names:
        if any(t["name"] == title_name for t in titles):
            continue
        try:
            import httpx
            response = httpx.get(
                f"{config.legislation_api_base}/Titles",
                params={"$filter": f"name eq '{title_name}'", "$top": 10},
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            values = response.json().get("value", [])
            match = next((item for item in values if item.get("name") == title_name), None)
            if match:
                titles.append(match)
            else:
                print(f"No exact Register title match: {title_name}")
        except Exception as exc:
            print(f"Could not resolve Register title {title_name}: {exc}")

    for title in titles:
        title_id = title["id"]
        metadata_path = raw_dir / f"{title_id}.json"
        html_path = raw_dir / f"{title_id}.html"
        if metadata_path.exists() and html_path.exists():
            index.append(json.loads(metadata_path.read_text()))
            continue
        version = get_current_version(title_id)
        if not version:
            print(f"Could not find a current Federal Register version: {title_id}")
            continue
        metadata, failure = fetch_one_title(title)
        if metadata:
            index.append(metadata)
        elif failure:
            print(f"Federal Register fetch failed: {failure}")

    (data_dir / "index.json").write_text(json.dumps(index, indent=2))

    # Save a small, reproducible registry rather than scraping dynamic search
    # pages. The later Award/Decision/Agreement fetchers will use these URLs.
    registry = {
        "fetched_at": __import__("datetime").datetime.now().isoformat(),
        "official_indexes": {
            **manifest.get("fair_work_commission", {}),
            **manifest.get("fair_work_ombudsman", {}),
        },
    }
    (data_dir / "official_indexes.json").write_text(json.dumps(registry, indent=2))
    print(f"V1 source fetch complete: {len(index)} Federal Register document(s).")
    print("FWC/FWO indexes recorded; bulk agreement and decision download is intentionally not enabled yet.")


if __name__ == "__main__":
    main()
