"""
Generate Obsidian-compatible Markdown wiki pages from the database.
  wiki/{act_slug}/index.md          — Act overview + TOC
  wiki/{act_slug}/{section_no}.md   — Section page with [[wikilinks]]
"""
import re
import psycopg2
from pathlib import Path
from tqdm import tqdm
from config import config

WIKI = Path(config.wiki_dir)
WIKI.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def section_link(act_slug: str, section_no: str, label: str = None) -> str:
    sec_slug = section_no.replace("(", "").replace(")", "").replace(" ", "-")
    display = label or f"s {section_no}"
    return f"[[{act_slug}/{sec_slug}|{display}]]"


def render_section_md(sec: dict, refs: list[dict], backlinks: list[dict],
                      entities: list[dict], act_slug: str) -> str:
    lines = []
    lines.append(f"# {sec['act_name']} — s {sec['section_no']}")
    if sec.get("section_heading"):
        lines.append(f"**{sec['section_heading']}**\n")
    lines.append(f"> *Compilation date: {sec['compilation_dt']}*\n")
    lines.append("---\n")
    lines.append(sec["body"])
    lines.append("")

    if refs:
        lines.append("## Cross-references")
        for r in refs:
            if r["to_section_no"]:
                lnk = section_link(act_slug, r["to_section_no"])
                label = r.get("to_act_name") or sec["act_name"]
                lines.append(f"- {lnk} — _{r['ref_text']}_ ({r['ref_type']})")
        lines.append("")

        # Mermaid is supported by Obsidian and many Markdown viewers. The web
        # UI uses the native SVG graph for the same relationship data.
        lines.append("## Relationship diagram")
        lines.append("```mermaid")
        lines.append("flowchart LR")
        lines.append(f'  CURRENT["s {sec["section_no"]}"]')
        for i, r in enumerate(refs[:8], 1):
            target = (r.get("to_section_no") or "unresolved").replace('"', "'")
            lines.append(f'  R{i}["s {target}"]')
            lines.append(f"  CURRENT -->|{r.get('ref_type') or 'reference'}| R{i}")
        lines.append("```")
        lines.append("")

    if backlinks:
        lines.append("## Referenced by")
        for b in backlinks:
            lnk = section_link(act_slug, b["from_section_no"])
            lines.append(f"- {lnk}")
        lines.append("")

    if entities:
        defns = [e for e in entities if e["entity_type"] == "definition"]
        obligs = [e for e in entities if e["entity_type"] == "obligation"]
        prohibs = [e for e in entities if e["entity_type"] == "prohibition"]

        if defns:
            lines.append("## Definitions")
            for d in defns:
                lines.append(f"- **{d['term']}**: {d['body'][:200]}")
            lines.append("")
        if obligs:
            lines.append("## Obligations")
            for o in obligs[:5]:
                lines.append(f"- {o['body'][:200]}")
            lines.append("")
        if prohibs:
            lines.append("## Prohibitions")
            for p in prohibs[:5]:
                lines.append(f"- {p['body'][:200]}")
            lines.append("")

    lines.append("---")
    lines.append(f"*Source: [{sec['act_name']} — s {sec['section_no']}]({sec['source_url']})*")
    return "\n".join(lines)


def render_act_index(act_name: str, sections: list[dict], act_slug: str) -> str:
    lines = [f"# {act_name}", ""]
    lines.append("## Table of Contents\n")
    for s in sections:
        indent = "  " * s["depth"]
        sec_slug = s["section_no"].replace("(","").replace(")","").replace(" ","-")
        heading = f" — {s['section_heading']}" if s.get("section_heading") else ""
        lines.append(f"{indent}- [[{act_slug}/{sec_slug}|s {s['section_no']}{heading}]]")
    return "\n".join(lines)


def main():
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()

    # all acts
    cur.execute("SELECT id, name FROM acts ORDER BY name")
    acts = cur.fetchall()

    for act_id, act_name in tqdm(acts, desc="Generating wiki pages"):
        act_slug = slugify(act_name)
        act_dir = WIKI / act_slug
        act_dir.mkdir(parents=True, exist_ok=True)

        # sections for this act (latest compilation)
        cur.execute("""
            SELECT s.id, s.section_no, s.section_heading, s.body,
                   s.depth, c.compilation_dt::text, s.source_url
            FROM sections s
            JOIN compilations c ON s.compilation_id = c.id
            WHERE s.act_id = %s AND c.is_latest = true
            ORDER BY s.id
        """, (act_id,))
        sections = [
            dict(zip(["id","section_no","section_heading","body",
                      "depth","compilation_dt","source_url"], r))
            for r in cur.fetchall()
        ]
        for s in sections:
            s["act_name"] = act_name

        if not sections:
            continue

        # write act index
        (act_dir / "index.md").write_text(render_act_index(act_name, sections, act_slug))

        # write each section
        sec_ids = [s["id"] for s in sections]

        # fetch refs in bulk
        cur.execute("""
            SELECT from_section_id, to_section_id, to_section_no, ref_text, ref_type, to_act_name
            FROM section_refs WHERE from_section_id = ANY(%s)
        """, (sec_ids,))
        refs_by_sec: dict[int, list] = {}
        for row in cur.fetchall():
            refs_by_sec.setdefault(row[0], []).append({
                "to_section_id": row[1], "to_section_no": row[2],
                "ref_text": row[3], "ref_type": row[4], "to_act_name": row[5],
            })

        # fetch backlinks in bulk
        cur.execute("""
            SELECT r.to_section_id, s.section_no as from_section_no
            FROM section_refs r
            JOIN sections s ON s.id = r.from_section_id
            WHERE r.to_section_id = ANY(%s)
        """, (sec_ids,))
        backlinks_by_sec: dict[int, list] = {}
        for row in cur.fetchall():
            backlinks_by_sec.setdefault(row[0], []).append({"from_section_no": row[1]})

        # fetch entities in bulk
        cur.execute("""
            SELECT section_id, entity_type, term, body
            FROM entities WHERE section_id = ANY(%s)
        """, (sec_ids,))
        entities_by_sec: dict[int, list] = {}
        for row in cur.fetchall():
            entities_by_sec.setdefault(row[0], []).append({
                "entity_type": row[1], "term": row[2], "body": row[3],
            })

        for s in sections:
            sec_slug = s["section_no"].replace("(","").replace(")","").replace(" ","-")
            md = render_section_md(
                s,
                refs_by_sec.get(s["id"], []),
                backlinks_by_sec.get(s["id"], []),
                entities_by_sec.get(s["id"], []),
                act_slug,
            )
            (act_dir / f"{sec_slug}.md").write_text(md)

    cur.close()
    conn.close()
    print(f"Wiki pages written to {WIKI}/")


if __name__ == "__main__":
    main()
