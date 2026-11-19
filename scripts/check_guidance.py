"""Validate the V3 guidance manifest and file formats."""
import json
from pathlib import Path

from config import config


def main() -> None:
    records = json.loads((Path(config.data_dir) / "guidance_index.json").read_text())
    ids = [record["id"] for record in records]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    missing = [record["id"] for record in records if not Path(record["path"]).is_file()]
    invalid_authority = [record["id"] for record in records
                         if record.get("authority_level") != "official_guidance"]
    if duplicates or missing or invalid_authority:
        raise SystemExit(
            f"Guidance manifest invalid: duplicates={duplicates}, missing={missing}, "
            f"authority={invalid_authority}"
        )
    print(f"Validated {len(records)} official FWO guidance records")


if __name__ == "__main__":
    main()
