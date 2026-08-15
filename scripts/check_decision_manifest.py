"""Validate the reviewable V4 FWC decision manifest before fetching."""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_RELATIONS = {"cites", "interprets", "concerns"}
OFFICIAL_HOSTS = {"www.fwc.gov.au", "web-prd.fwc.gov.au"}


def main() -> None:
    records = json.loads(Path("config/decisions_v4.json").read_text())
    ids = [record.get("id") for record in records]
    assert records and len(ids) == len(set(ids)), "Decision IDs must be present and unique"
    for record in records:
        assert record.get("case_name") and record.get("citation"), record
        parsed = urlparse(record.get("url", ""))
        assert parsed.scheme == "https" and parsed.hostname in OFFICIAL_HOSTS, record["id"]
        date.fromisoformat(record["decision_date"])
        for relation in record.get("relations", []):
            assert relation.get("type") in ALLOWED_RELATIONS, relation
            assert any(key in relation for key in ("target_title", "target_award", "target_enterprise_agreement")), relation
    print(f"V4 decision manifest passed: {len(records)} records")


if __name__ == "__main__":
    main()
