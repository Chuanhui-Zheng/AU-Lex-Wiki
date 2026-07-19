"""
Auto-generate evaluation QA pairs across four question types:
  locate    — find the section that answers a factual question
  cross_ref — multi-hop: follow a cross-reference chain
  temporal  — same section, two compilation dates
  refusal   — non-existent section (expect "not found" answer)
"""
import json
import random
import psycopg2
from pathlib import Path
from tqdm import tqdm
from config import config

OUT = Path(config.data_dir) / "eval_set"
OUT.mkdir(parents=True, exist_ok=True)

OBLIGATION_TEMPLATES = [
    "What must {party} do under {act} section {sec}?",
    "What are the requirements imposed by section {sec} of {act}?",
    "Describe the obligations in section {sec} of {act}.",
]
DEFINITION_TEMPLATES = [
    "How is '{term}' defined under {act}?",
    "What does '{term}' mean in the context of {act}?",
]
LOCATE_TEMPLATES = [
    "Which section of {act} deals with {heading}?",
    "What does {act} section {sec} say about {heading}?",
]
FAKE_SECTION_POOL = [
    "999", "488A", "1024(3)", "77ZZZ", "301B(4)(ii)", "555(1A)",
    "88(9)", "212C", "400AA", "13ZA(7)",
]


def gen_locate(cur, n: int = 150) -> list[dict]:
    cur.execute("""
        SELECT s.id, s.section_no, s.section_heading, s.body, a.name
        FROM sections s JOIN acts a ON a.id = s.act_id
        JOIN compilations c ON c.id = s.compilation_id
        WHERE c.is_latest = true
          AND s.section_heading IS NOT NULL
          AND char_length(s.body) > 100
        ORDER BY random() LIMIT %s
    """, (n * 3,))
    rows = cur.fetchall()
    random.shuffle(rows)
    questions = []
    for sid, sno, heading, body, act_name in rows[:n]:
        tmpl = random.choice(LOCATE_TEMPLATES)
        q = tmpl.format(act=act_name, sec=sno, heading=heading)
        questions.append({
            "question": q,
            "expected_answer": f"Section {sno} of {act_name}: {body[:300]}",
            "source_section_ids": [sid],
            "question_type": "locate",
            "act_name": act_name,
        })
    return questions


def gen_cross_ref(cur, n: int = 100) -> list[dict]:
    cur.execute("""
        SELECT r.from_section_id, r.to_section_id,
               s1.section_no, s1.body, s2.section_no, s2.body,
               a.name
        FROM section_refs r
        JOIN sections s1 ON s1.id = r.from_section_id
        JOIN sections s2 ON s2.id = r.to_section_id
        JOIN acts a ON a.id = s1.act_id
        JOIN compilations c ON c.id = s1.compilation_id
        WHERE r.to_section_id IS NOT NULL
          AND c.is_latest = true
        ORDER BY random() LIMIT %s
    """, (n,))
    rows = cur.fetchall()
    questions = []
    for fsid, tsid, fsno, fbody, tsno, tbody, act_name in rows:
        q = (f"Section {fsno} of {act_name} references section {tsno}. "
             f"What does the referenced section require?")
        questions.append({
            "question": q,
            "expected_answer": f"Section {tsno} of {act_name}: {tbody[:300]}",
            "source_section_ids": [fsid, tsid],
            "question_type": "cross_ref",
            "act_name": act_name,
        })
    return questions


def gen_temporal(cur, n: int = 50) -> list[dict]:
    # Find acts with multiple compilations
    cur.execute("""
        SELECT s1.id, s2.id, s1.section_no, s1.body, s2.body,
               c1.compilation_dt::text, c2.compilation_dt::text, a.name
        FROM sections s1
        JOIN sections s2 ON s2.section_no = s1.section_no AND s2.act_id = s1.act_id
        JOIN compilations c1 ON c1.id = s1.compilation_id
        JOIN compilations c2 ON c2.id = s2.compilation_id
        JOIN acts a ON a.id = s1.act_id
        WHERE c1.compilation_dt != c2.compilation_dt
          AND c1.compilation_dt < c2.compilation_dt
          AND s1.body != s2.body
        ORDER BY random() LIMIT %s
    """, (n,))
    rows = cur.fetchall()
    questions = []
    for s1id, s2id, sno, body1, body2, dt1, dt2, act_name in rows:
        q = (f"As of {dt2}, what does section {sno} of {act_name} say? "
             f"How does this differ from the {dt1} version?")
        questions.append({
            "question": q,
            "expected_answer": (
                f"As of {dt2}: {body2[:200]}\n"
                f"Previously ({dt1}): {body1[:200]}"
            ),
            "source_section_ids": [s1id, s2id],
            "question_type": "temporal",
            "act_name": act_name,
        })
    return questions


def gen_refusal(cur, n: int = 50) -> list[dict]:
    cur.execute("SELECT name FROM acts ORDER BY random() LIMIT %s", (n,))
    act_names = [r[0] for r in cur.fetchall()]
    questions = []
    for act_name in act_names:
        fake_sec = random.choice(FAKE_SECTION_POOL)
        q = f"What does section {fake_sec} of {act_name} say?"
        questions.append({
            "question": q,
            "expected_answer": "not_found",
            "source_section_ids": [],
            "question_type": "refusal",
            "act_name": act_name,
        })
    return questions


def main():
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()

    all_qs = []
    print("Generating locate questions...")
    all_qs.extend(gen_locate(cur, 200))
    print("Generating cross-ref questions...")
    all_qs.extend(gen_cross_ref(cur, 150))
    print("Generating temporal questions...")
    all_qs.extend(gen_temporal(cur, 50))
    print("Generating refusal questions...")
    all_qs.extend(gen_refusal(cur, 50))

    random.shuffle(all_qs)

    out_path = OUT / "eval_questions.jsonl"
    with out_path.open("w") as f:
        for q in all_qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    # also insert into DB
    for q in tqdm(all_qs, desc="Inserting eval questions"):
        cur.execute(
            """INSERT INTO eval_questions
               (question, expected_answer, source_section_ids, question_type, act_name)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (q["question"], q["expected_answer"],
             q["source_section_ids"], q["question_type"], q["act_name"]),
        )
    conn.commit()
    cur.close()
    conn.close()

    print(f"\nGenerated {len(all_qs)} questions → {out_path}")
    by_type = {}
    for q in all_qs:
        by_type[q["question_type"]] = by_type.get(q["question_type"], 0) + 1
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
