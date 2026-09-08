"""Validate the V5 agreement manifest and local provenance metadata."""
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    records = json.loads(Path("config/agreements_v5.json").read_text())
    ids = [record.get("agreement_id") for record in records]
    assert len(records) == 6 and len(ids) == len(set(ids))
    expected_industries = {"Clerks", "Retail", "Hospitality", "Professional Employees", "Aged Care", "Transport"}
    assert {record["industry"] for record in records} == expected_industries
    for record in records:
        parsed = urlparse(record["url"])
        assert parsed.scheme == "https" and parsed.hostname == "www.fwc.gov.au"
        path = Path("data/raw/agreements") / f"{record['agreement_id'].lower()}.pdf"
        assert path.is_file() and path.read_bytes().startswith(b"%PDF"), record["agreement_id"]
        if record.get("approval_date"):
            date.fromisoformat(record["approval_date"])
        if record.get("nominal_expiry"):
            date.fromisoformat(record["nominal_expiry"])
    print(f"V5 agreement manifest passed: {len(records)} official PDFs across {len(expected_industries)} industries")


if __name__ == "__main__":
    main()
