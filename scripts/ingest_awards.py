"""Run the V2 Modern Awards pipeline without enabling local embeddings.

The fetch step is explicit and networked. Parsing and ingestion are local and
idempotent, so a user can refresh official sources without deleting the Atlas.
"""
import subprocess
import sys


def run(module: str, *args: str) -> None:
    subprocess.run([sys.executable, "-m", module, *args], check=True)


def main() -> None:
    run("scripts.fetch_awards")
    run("scripts.parse_awards")
    run("scripts.embed_and_ingest", "--skip-embedding")
    print("Modern Awards V2 ingestion complete (text-only; no BGE-M3 vectors).")


if __name__ == "__main__":
    main()
