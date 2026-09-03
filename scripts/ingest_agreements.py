"""Run the selected V5 Enterprise Agreements pipeline in text-only mode."""
import subprocess
import sys


def run(module: str, *args: str) -> None:
    subprocess.run([sys.executable, "-m", module, *args], check=True)


def main() -> None:
    run("scripts.fetch_agreements")
    run("scripts.parse_agreements")
    run("scripts.embed_and_ingest", "--skip-embedding")
    run("scripts.link_agreements")
    print("Enterprise Agreements V5 ingestion complete (text-only).")


if __name__ == "__main__":
    main()
