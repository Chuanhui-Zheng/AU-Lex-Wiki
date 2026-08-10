"""Run the WorkLaw text pipeline after the official source fetch step."""
import subprocess
import sys

PYTHON = sys.executable
STEPS = [
    ("Parsing source documents → provision chunks", ["python", "-m", "scripts.parse_sections"]),
    ("Ingesting to PostgreSQL (text + metadata)",
     ["python", "-m", "scripts.embed_and_ingest", "--skip-embedding"]),
    ("Extracting legal entities and cross-references",
     ["python", "-m", "scripts.extract_entities"]),
    ("Generating Markdown wiki pages",
     ["python", "-m", "scripts.generate_markdown"]),
]

if __name__ == "__main__":
    import os
    env = {**os.environ, "PYTHONPATH": "."}
    for desc, cmd in STEPS:
        print(f"\n── {desc} ──")
        result = subprocess.run([PYTHON] + cmd[1:], env=env)
        if result.returncode != 0:
            print(f"Step failed: {cmd}")
            sys.exit(1)
    print("\nPipeline complete.")
