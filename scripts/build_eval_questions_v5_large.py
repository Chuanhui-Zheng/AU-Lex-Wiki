"""Build a deterministic, stratified V5 retrieval/refusal benchmark.

The generated set is derived from the indexed corpus, but every question keeps
an explicit gold title and optional section/term checks.  This makes the set
reproducible without pretending that synthetic questions are a production QA
set.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import psycopg2

from config import config


OUTPUT = Path("config/eval_questions_v5_large.json")


def alias_for(title: str, document_type: str) -> str:
    value = re.sub(r"\s*\[[A-Z]{2}\d+\]", "", title).strip()
    value = re.sub(r"\s*\([^)]*\)", "", value).strip()
    if document_type == "award":
        value = value.replace("Industry", "").replace(" - Private Sector", "")
    if document_type == "guidance":
        value = re.sub(r"^(Your guide to|A guide to|Guide to)\s*", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def term_for(body: str, heading: str | None) -> str:
    text = f"{heading or ''} {body}".lower()
    for term in ("overtime", "minimum rates", "penalty rates", "casual", "leave", "classification", "consultation", "dismissal", "sunday", "hours"):
        if term in text:
            return term
    return "employee"


def main() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    questions: list[dict] = []
    try:
        cur.execute("""
            SELECT a.name, a.document_type, s.section_no, s.section_heading, s.body
            FROM sections s
            JOIN acts a ON a.id=s.act_id
            JOIN compilations c ON c.id=s.compilation_id
            WHERE a.document_type='legislation' AND c.is_latest=true
            ORDER BY a.id, length(s.body) DESC, s.id
        """)
        legislation = cur.fetchall()
        legislation_counts: dict[str, int] = {}
        for index, (title, doc_type, section_no, heading, body) in enumerate(legislation):
            legislation_counts[title] = legislation_counts.get(title, 0) + 1
            if legislation_counts[title] > 6:
                continue
            if len(questions) >= 12:
                break
            short = "Fair Work Act" if "Act" in title else "Fair Work Regulations"
            questions.append({
                "id": f"legislation-{index + 1:02d}",
                "bucket": "legislation",
                "query_style": "authority_alias",
                "question": f"What does section {section_no} of the {short} provide?",
                "target_title": title,
                "expected_section": section_no,
                "expected_terms": [term_for(body, heading)],
                "in_scope": True,
            })

        cur.execute("""
            SELECT DISTINCT ON (a.id) a.name, a.document_type, s.section_heading, s.body
            FROM sections s
            JOIN acts a ON a.id=s.act_id
            JOIN compilations c ON c.id=s.compilation_id
            WHERE a.document_type='award' AND c.is_latest=true
            ORDER BY a.id, length(s.body) DESC, s.id
        """)
        awards = cur.fetchall()
        for index, (title, doc_type, heading, body) in enumerate(awards[:24]):
            topic = term_for(body, heading)
            style = "title_explicit" if index < 12 else "authority_alias"
            subject = title if style == "title_explicit" else alias_for(title, doc_type)
            questions.append({
                "id": f"award-{index + 1:02d}",
                "bucket": "award",
                "query_style": style,
                "question": f"What does the {subject} say about {topic}?",
                "target_title": title,
                "expected_terms": [topic],
                "in_scope": True,
            })

        cur.execute("""
            SELECT DISTINCT ON (a.id) a.name, a.document_type, s.section_heading, s.body
            FROM sections s
            JOIN acts a ON a.id=s.act_id
            JOIN compilations c ON c.id=s.compilation_id
            WHERE a.document_type='guidance' AND c.is_latest=true
            ORDER BY a.id, length(s.body) DESC, s.id
        """)
        guidance = cur.fetchall()
        for index, (title, doc_type, heading, body) in enumerate(guidance[:10]):
            style = "title_explicit" if index < 5 else "authority_alias"
            subject = title if style == "title_explicit" else alias_for(title, doc_type)
            topic = term_for(body, heading)
            questions.append({
                "id": f"guidance-{index + 1:02d}",
                "bucket": "guidance",
                "query_style": style,
                "question": f"What does the Fair Work Ombudsman material on {subject} explain about {topic}?",
                "target_title": title,
                "expected_terms": [topic],
                "in_scope": True,
            })

        cur.execute("""
            SELECT d.case_name, d.citation, a.name
            FROM decisions d JOIN acts a ON a.id=d.act_id
            ORDER BY d.decision_date NULLS LAST, d.decision_id
        """)
        for index, (case_name, citation, title) in enumerate(cur.fetchall()):
            subject = citation if index < 4 else case_name.split(" v ")[0]
            questions.append({
                "id": f"decision-{index + 1:02d}",
                "bucket": "decision",
                "query_style": "citation" if index < 4 else "party_alias",
                "question": f"What issue is discussed in the Fair Work Commission decision {subject}?",
                "target_title": title,
                "expected_terms": ["decision"],
                "in_scope": True,
            })

        cur.execute("""
            SELECT a.name, ea.industry
            FROM enterprise_agreements ea JOIN acts a ON a.id=ea.act_id
            ORDER BY ea.agreement_id
        """)
        for index, (title, industry) in enumerate(cur.fetchall()):
            subject = title if index < 4 else f"{industry} enterprise agreement"
            questions.append({
                "id": f"agreement-{index + 1:02d}",
                "bucket": "enterprise_agreement",
                "query_style": "title_explicit" if index < 4 else "industry_alias",
                "question": f"What indexed conditions are covered by the {subject}?",
                "target_title": title,
                "expected_terms": ["employee"],
                "in_scope": True,
            })
    finally:
        cur.close()
        conn.close()

    refusal_questions = [
        ("moon", "What is the moon made of?"),
        ("weather", "What will the weather be tomorrow?"),
        ("stock", "Should I buy shares in a technology company today?"),
        ("recipe", "How do I bake a chocolate cake?"),
        ("football", "Who will win the next football match?"),
        ("medical", "What dosage should I take for a headache?"),
        ("immigration", "Can I get a visa for another country?"),
        ("tax", "How should I calculate my personal income tax?"),
        ("travel", "What hotel should I book in Sydney?"),
        ("crypto", "Which cryptocurrency will rise next month?"),
        ("astrology", "What does my horoscope say this week?"),
        ("sports", "What was yesterday's basketball score?"),
        ("music", "Write me a song about summer."),
        ("coding", "How do I implement a sorting algorithm?"),
        ("geography", "What is the capital of Brazil?"),
        ("shopping", "Which laptop should I buy?"),
        ("legal-advice", "Should I sue my employer for damages?"),
        ("prediction", "Will my employer be found liable in court?"),
        ("personal", "Is my manager secretly monitoring me?"),
        ("politics", "Who should I vote for in the next election?"),
    ]
    for key, question in refusal_questions:
        questions.append({
            "id": f"refusal-{key}",
            "bucket": "refusal",
            "query_style": "out_of_scope",
            "question": question,
            "target_title": "",
            "expected_terms": [],
            "in_scope": False,
        })

    OUTPUT.write_text(json.dumps(questions, indent=2) + "\n")
    counts: dict[str, int] = {}
    for question in questions:
        counts[question["bucket"]] = counts.get(question["bucket"], 0) + 1
    print(f"Wrote {len(questions)} V5 questions: {counts}")


if __name__ == "__main__":
    main()
