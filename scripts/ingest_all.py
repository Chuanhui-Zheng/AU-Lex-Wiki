"""Run the complete AU-WorkLaw-Atlas ingestion in one reproducible command.

The default profile is text-only: it downloads official sources, parses every
configured V1–V5 source, ingests PostgreSQL text/metadata, links graph edges,
materializes the V6 graph and runs integrity checks. Use --with-embeddings only
when BGE-M3 is already installed and local vector storage is intended.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg2

from config import config


ROOT = Path(__file__).resolve().parents[1]


def apply_schema() -> None:
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute((ROOT / "db" / "schema.sql").read_text())
        conn.commit()
    finally:
        cur.close()
        conn.close()


def run(module: str, *args: str, dry_run: bool = False) -> None:
    command = [sys.executable, "-m", module, *args]
    print(f"\n── {module}{' ' + ' '.join(args) if args else ''} ──")
    if dry_run:
        print("DRY RUN:", " ".join(command))
        return
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest all configured WorkLaw sources")
    parser.add_argument("--skip-fetch", action="store_true", help="Reuse existing raw source files and skip network fetches")
    parser.add_argument("--with-embeddings", action="store_true", help="Run BGE-M3 encoding instead of the default text-only ingest")
    parser.add_argument("--dry-run", action="store_true", help="Print the pipeline without changing the database or files")
    args = parser.parse_args()

    print("AU-WorkLaw-Atlas full ingestion")
    print(f"Database: {config.db_url}")
    print(f"Embeddings: {'enabled' if args.with_embeddings else 'disabled (text-only)'}")
    if args.dry_run:
        print("Schema: db/schema.sql")
    else:
        print("\n── Applying PostgreSQL schema ──")
        apply_schema()

    if not args.skip_fetch:
        run("scripts.fetch_worklaw_sources", dry_run=args.dry_run)
        run("scripts.fetch_awards", dry_run=args.dry_run)
    run("scripts.check_awards", dry_run=args.dry_run)
    run("scripts.parse_awards", dry_run=args.dry_run)
    run("scripts.parse_sections", dry_run=args.dry_run)

    if not args.skip_fetch:
        run("scripts.fetch_guidance", dry_run=args.dry_run)
    run("scripts.check_guidance", dry_run=args.dry_run)
    run("scripts.parse_guidance", dry_run=args.dry_run)

    if not args.skip_fetch:
        run("scripts.fetch_decisions", dry_run=args.dry_run)
    run("scripts.parse_decisions", dry_run=args.dry_run)

    if not args.skip_fetch:
        run("scripts.fetch_agreements", dry_run=args.dry_run)
    run("scripts.parse_agreements", dry_run=args.dry_run)

    embedding_args = () if args.with_embeddings else ("--skip-embedding",)
    run("scripts.embed_and_ingest", *embedding_args, dry_run=args.dry_run)
    run("scripts.extract_entities", "--reset-derived", dry_run=args.dry_run)

    run("scripts.link_decisions", dry_run=args.dry_run)
    run("scripts.check_decisions", dry_run=args.dry_run)
    run("scripts.link_agreements", dry_run=args.dry_run)
    run("scripts.check_agreements", dry_run=args.dry_run)
    run("scripts.resolve_cross_act_refs_v6", dry_run=args.dry_run)
    run("scripts.materialize_graph_v6", dry_run=args.dry_run)
    run("scripts.check_cross_act_refs_v6", dry_run=args.dry_run)
    run("scripts.check_graph_v6", dry_run=args.dry_run)
    print("\nFull ingestion complete: sources, PostgreSQL, graph projection and checks passed.")


if __name__ == "__main__":
    main()
