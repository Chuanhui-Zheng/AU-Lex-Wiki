"""Validate the downloaded V2 Award manifest before ingestion."""
import json
from pathlib import Path

from config import config


def main() -> None:
    manifest_path = Path(config.data_dir) / "awards_index.json"
    records = json.loads(manifest_path.read_text())
    codes = [item["code"] for item in records]
    duplicate_codes = sorted({code for code in codes if codes.count(code) > 1})
    missing_html = [item["code"] for item in records if not Path(item["html_path"]).is_file()]
    missing_guides = [item["code"] for item in records if item.get("pay_guide_status") == "missing"]
    if duplicate_codes or missing_html:
        raise SystemExit(
            f"Award manifest invalid: duplicates={duplicate_codes}, missing_html={missing_html}"
        )
    print(f"Validated {len(records)} Award records")
    print(f"Pay Guides unavailable: {len(missing_guides)}")


if __name__ == "__main__":
    main()
