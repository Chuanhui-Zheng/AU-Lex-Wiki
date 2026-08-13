"""
Encode section chunks with BGE-M3 (dense + sparse) and upsert into PostgreSQL.
Pass --skip-embedding to ingest text/metadata only (no model download required).
"""
import json
import argparse
import psycopg2
from pgvector.psycopg2 import register_vector
from pathlib import Path
from tqdm import tqdm
from config import config

_model = None


def get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        _model = BGEM3FlagModel(config.embedding_model, use_fp16=True)
    return _model


def encode_batch(texts: list[str]) -> tuple[list, list]:
    out = get_model().encode(
        texts,
        batch_size=config.embed_batch_size,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    dense = out["dense_vecs"].tolist()
    sparse = [
        {str(k): float(v) for k, v in weights.items()}
        for weights in out["lexical_weights"]
    ]
    return dense, sparse


def ingest(conn, skip_embedding: bool = False):
    register_vector(conn)
    cur = conn.cursor()

    # Build act_id and compilation_id lookup from DB
    cur.execute("SELECT id, name FROM acts")
    act_map = {name: aid for aid, name in cur.fetchall()}

    cur.execute("SELECT id, document_id FROM compilations")
    comp_map = {doc_id: cid for cid, doc_id in cur.fetchall()}

    chunks_dir = Path(config.data_dir) / "chunks"
    jsonl_files = list(chunks_dir.glob("*.jsonl"))

    for jf in tqdm(jsonl_files, desc="Ingesting"):
        lines = jf.read_text().splitlines()
        sections = [json.loads(l) for l in lines if l.strip()]

        # check if already ingested (by act name + section_no)
        if sections:
            act_id = act_map.get(sections[0]["actName"])
            if act_id is None:
                # insert act first
                cur.execute(
                    "INSERT INTO acts (title_id, name, year) VALUES (%s, %s, %s) "
                    "ON CONFLICT (title_id) DO UPDATE SET name=EXCLUDED.name "
                    "RETURNING id",
                    (sections[0]["titleId"], sections[0]["actName"],
                     int(sections[0]["compilationDate"][:4]) if sections[0].get("compilationDate") else None),
                )
                act_id = cur.fetchone()[0]
                act_map[sections[0]["actName"]] = act_id

            comp_id = comp_map.get(sections[0]["documentId"])
            if comp_id is None:
                cur.execute("UPDATE compilations SET is_latest = false WHERE act_id=%s", (act_id,))
                cur.execute(
                    "INSERT INTO compilations (act_id, document_id, compilation_dt, is_latest, xml_path) "
                    "VALUES (%s, %s, %s, true, %s) ON CONFLICT (document_id) DO NOTHING RETURNING id",
                    (act_id, sections[0]["documentId"],
                     sections[0].get("compilationDate") or "1900-01-01",
                     sections[0].get("xmlPath", "")),
                )
                row = cur.fetchone()
                if row:
                    comp_id = row[0]
                    comp_map[sections[0]["documentId"]] = comp_id
                else:
                    cur.execute("SELECT id FROM compilations WHERE document_id=%s",
                                (sections[0]["documentId"],))
                    comp_id = cur.fetchone()[0]

            # Only the current compilation for an Act participates in search.
            cur.execute("UPDATE compilations SET is_latest = (id=%s) WHERE act_id=%s",
                        (comp_id, act_id))

        # batch encode or skip
        for batch_start in range(0, len(sections), config.embed_batch_size):
            batch = sections[batch_start: batch_start + config.embed_batch_size]
            batch_texts = [s["body"] for s in batch]

            if skip_embedding:
                pairs = [(None, None)] * len(batch)
            else:
                dense_vecs, sparse_vecs = encode_batch(batch_texts)
                pairs = list(zip(dense_vecs, sparse_vecs))

            for s, (dvec, svec) in zip(batch, pairs):
                a_id = act_map.get(s["actName"], act_id)
                c_id = comp_map.get(s["documentId"], comp_id)
                # Keep re-runs idempotent without requiring a destructive
                # cleanup or a unique index on the existing database.
                cur.execute(
                    "SELECT id, embedding IS NOT NULL FROM sections "
                    "WHERE compilation_id=%s AND section_no=%s AND body=%s LIMIT 1",
                    (c_id, s["sectionNo"], s["body"]),
                )
                existing = cur.fetchone()
                if existing and (skip_embedding or existing[1]):
                    continue
                if existing:
                    cur.execute(
                        "UPDATE sections SET embedding=%s, sparse_weights=%s WHERE id=%s",
                        (dvec, json.dumps(svec) if svec else None, existing[0]),
                    )
                    continue
                cur.execute(
                    """INSERT INTO sections
                       (compilation_id, act_id, eid, section_no, section_heading,
                        parent_no, depth, body, embedding, sparse_weights, source_url)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    (c_id, a_id, s.get("eid",""), s["sectionNo"],
                     s.get("sectionHeading",""), s.get("parentNo",""),
                     s.get("depth", 0), s["body"],
                     dvec, json.dumps(svec) if svec else None,
                     s.get("sourceUrl","")),
                )

    conn.commit()
    cur.close()
    label = "text-only" if skip_embedding else "with embeddings"
    print(f"Ingest complete ({label}).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-embedding", action="store_true",
                        help="Ingest text and metadata only; skip BGE-M3 encoding")
    args = parser.parse_args()
    conn = psycopg2.connect(config.db_url)
    ingest(conn, skip_embedding=args.skip_embedding)
    conn.close()


if __name__ == "__main__":
    main()
