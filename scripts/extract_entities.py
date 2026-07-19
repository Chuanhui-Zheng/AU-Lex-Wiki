"""
Extract entities and cross-references from parsed section chunks.
Two passes:
  1. Structural: regex patterns on legal text (fast, no API cost)
  2. Semantic:   Claude API for definitions / obligations (optional, --semantic flag)
"""
import json
import re
import argparse
import psycopg2
from pathlib import Path
from tqdm import tqdm
from config import config

# ── Regex patterns ────────────────────────────────────────────────────────────

# Cross-references: "section 18(1)", "s 30EK", "reg 12", "paragraph (a)"
XREF_RE = re.compile(
    r"\b(?:section|subsection|paragraph|subparagraph|regulation|reg|s\.?)\s+"
    r"(\d+[A-Z]*(?:\([a-zA-Z0-9]+\))*)",
    re.IGNORECASE,
)

# Definitions: 'X' means Y  |  "X" means Y  |  X has the meaning
DEFN_RE = re.compile(
    r'["‘“]([^""‘“’”]{2,60})["’”]\s+(?:means|includes|has the meaning)',
    re.IGNORECASE,
)

# Obligations: must / shall
OBLIG_RE = re.compile(r"\b(must|shall)\b", re.IGNORECASE)

# Prohibitions: must not / shall not
PROHIB_RE = re.compile(r"\b(must not|shall not)\b", re.IGNORECASE)

# Delegation / power
DELEG_RE = re.compile(r"\b(may|is authorised to|has power to)\b", re.IGNORECASE)

# Penalty
PENALTY_RE = re.compile(r"\b(\d+)\s+penalty units?\b", re.IGNORECASE)


def classify_ref_type(context: str) -> str:
    if re.search(r"\bmeans\b|\bincludes\b", context, re.I):
        return "definition"
    if re.search(r"\bsubject to\b|\bdespite\b|\boverrides\b", context, re.I):
        return "override"
    if re.search(r"\bdelegate[sd]?\b|\bauthorise[sd]?\b", context, re.I):
        return "delegation"
    return "cross_ref"


def extract_structural(section: dict) -> dict:
    body = section["body"]
    xrefs = []
    for m in XREF_RE.finditer(body):
        start = max(0, m.start() - 40)
        context = body[start: m.end() + 40]
        xrefs.append({
            "toSectionNo": m.group(1),
            "refText": m.group(0),
            "refType": classify_ref_type(context),
        })

    entities = []
    for m in DEFN_RE.finditer(body):
        entities.append({"type": "definition", "term": m.group(1),
                          "body": body[max(0, m.start()-20): m.end()+80]})
    for m in OBLIG_RE.finditer(body):
        if not PROHIB_RE.search(body[max(0,m.start()-5):m.end()+5]):
            entities.append({"type": "obligation", "term": None,
                              "body": body[max(0,m.start()-30):m.end()+120]})
    for m in PROHIB_RE.finditer(body):
        entities.append({"type": "prohibition", "term": None,
                          "body": body[max(0,m.start()-30):m.end()+120]})
    for m in DELEG_RE.finditer(body):
        entities.append({"type": "delegation", "term": None,
                          "body": body[max(0,m.start()-30):m.end()+120]})
    for m in PENALTY_RE.finditer(body):
        entities.append({"type": "penalty", "term": f"{m.group(1)} penalty units",
                          "body": body[max(0,m.start()-30):m.end()+60]})

    return {"xrefs": xrefs, "entities": entities}


def ingest_to_db(conn):
    cur = conn.cursor()

    # load all section rows into memory for fast lookup by (act_name, section_no)
    cur.execute("SELECT id, act_id, section_no, compilation_id FROM sections")
    rows = cur.fetchall()
    # index by (act_id, section_no) → section id  (keep latest compilation)
    by_section_no: dict[tuple, int] = {}
    for sid, aid, sno, cid in rows:
        key = (aid, sno)
        if key not in by_section_no:
            by_section_no[key] = sid

    # act name → act_id
    cur.execute("SELECT id, name FROM acts")
    act_map = {name: aid for aid, name in cur.fetchall()}

    chunks_dir = Path(config.data_dir) / "chunks"
    jsonl_files = list(chunks_dir.glob("*.jsonl"))

    for jf in tqdm(jsonl_files, desc="Extracting entities"):
        with jf.open() as f:
            for line in f:
                sec = json.loads(line)
                act_id = act_map.get(sec["actName"])
                if act_id is None:
                    continue
                sec_id = by_section_no.get((act_id, sec["sectionNo"]))
                if sec_id is None:
                    continue

                result = extract_structural(sec)

                # insert cross-references
                for xr in result["xrefs"]:
                    to_sec_id = by_section_no.get((act_id, xr["toSectionNo"]))
                    cur.execute(
                        """INSERT INTO section_refs
                           (from_section_id, to_section_id, to_act_name, to_section_no, ref_text, ref_type)
                           SELECT %s, %s, %s, %s, %s, %s
                           WHERE NOT EXISTS (
                             SELECT 1 FROM section_refs
                             WHERE from_section_id=%s
                               AND to_section_id IS NOT DISTINCT FROM %s
                               AND to_act_name IS NOT DISTINCT FROM %s
                               AND to_section_no IS NOT DISTINCT FROM %s
                               AND ref_text IS NOT DISTINCT FROM %s
                               AND ref_type=%s
                           )""",
                        (sec_id, to_sec_id, sec["actName"],
                         xr["toSectionNo"], xr["refText"], xr["refType"],
                         sec_id, to_sec_id, sec["actName"], xr["toSectionNo"],
                         xr["refText"], xr["refType"]),
                    )

                # insert entities (deduplicate by body prefix)
                seen_bodies = set()
                for ent in result["entities"]:
                    key = ent["body"][:60]
                    if key in seen_bodies:
                        continue
                    seen_bodies.add(key)
                    cur.execute(
                        """INSERT INTO entities (section_id, entity_type, term, body)
                           SELECT %s, %s, %s, %s
                           WHERE NOT EXISTS (
                             SELECT 1 FROM entities
                             WHERE section_id=%s AND entity_type=%s
                               AND term IS NOT DISTINCT FROM %s AND body=%s
                           )""",
                        (sec_id, ent["type"], ent.get("term"), ent["body"],
                         sec_id, ent["type"], ent.get("term"), ent["body"]),
                    )

    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic", action="store_true",
                        help="Also run Claude API for semantic entity extraction")
    args = parser.parse_args()

    conn = psycopg2.connect(config.db_url)
    print("Extracting structural entities and cross-references...")
    ingest_to_db(conn)
    conn.close()

    if args.semantic:
        print("Semantic extraction via LLM not implemented in this script. "
              "See pipeline/rag_pipeline.py for LLM usage.")

    print("Done.")


if __name__ == "__main__":
    main()
