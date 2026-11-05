"""Run the curated V4 decisions pipeline."""
import subprocess
import sys


def run(module: str, *args: str) -> None:
    subprocess.run([sys.executable, "-m", module, *args], check=True)


def main() -> None:
    run("scripts.fetch_decisions")
    run("scripts.parse_decisions")
    run("scripts.embed_and_ingest", "--skip-embedding")
    run("scripts.link_decisions")
    print("FWC decisions V4 ingestion complete (text-only).")


if __name__ == "__main__":
    main()
