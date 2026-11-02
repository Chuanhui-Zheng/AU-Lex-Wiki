"""Run deterministic V6 Graph-RAG release checks."""
from __future__ import annotations

import subprocess
import sys


CHECKS = (
    "scripts.check_graph_v6",
    "scripts.check_cross_act_refs_v6",
    "scripts.check_v6_api_contract",
)


def main() -> None:
    for module in CHECKS:
        print(f"[V6 acceptance] python -m {module}")
        subprocess.run([sys.executable, "-m", module], check=True)
    print(f"V6 acceptance passed: {len(CHECKS)} checks")


if __name__ == "__main__":
    main()
