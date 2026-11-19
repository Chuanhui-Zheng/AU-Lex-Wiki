"""Run the V3 official-guidance pipeline in a repeatable text-only profile."""
import subprocess
import sys


def run(module: str, *args: str) -> None:
    subprocess.run([sys.executable, "-m", module, *args], check=True)


def main() -> None:
    run("scripts.fetch_guidance")
    run("scripts.parse_guidance")
    run("scripts.embed_and_ingest", "--skip-embedding")
    print("FWO guidance V3 ingestion complete (official guidance; text-only).")


if __name__ == "__main__":
    main()
