"""Validate the fixed V5 benchmark before using its numbers."""
import json
from collections import Counter
from pathlib import Path

import psycopg2

from config import config


SET = Path("config/eval_questions_v5_large.json")


def main() -> None:
    questions = json.loads(SET.read_text())
    assert len(questions) == 79
    assert len({item["id"] for item in questions}) == len(questions)
    assert len({item["question"] for item in questions}) == len(questions)
    assert Counter(item["bucket"] for item in questions) == Counter({
        "legislation": 12,
        "award": 24,
        "guidance": 10,
        "decision": 7,
        "enterprise_agreement": 6,
        "refusal": 20,
    })
    assert sum(item.get("query_style") in {"authority_alias", "party_alias", "industry_alias"} for item in questions) >= 30
    answerable = [item for item in questions if item["in_scope"]]
    assert all(item["target_title"] and item["expected_terms"] for item in answerable)

    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        missing = []
        for item in answerable:
            cur.execute("SELECT 1 FROM acts WHERE lower(name)=lower(%s) LIMIT 1", (item["target_title"],))
            if not cur.fetchone():
                missing.append(item["target_title"])
    finally:
        cur.close()
        conn.close()
    assert not missing, missing
    print("V5 large evaluation set passed: 79 unique questions, 34 alias cases, all gold sources indexed")


if __name__ == "__main__":
    main()
