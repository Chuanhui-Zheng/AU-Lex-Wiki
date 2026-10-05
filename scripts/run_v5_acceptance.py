"""Run the deterministic V5 release checks in one command."""
from __future__ import annotations

import subprocess
import sys


CHECKS = (
    "scripts.check_agreements",
    "scripts.check_agreement_data",
    "scripts.check_v5_counts",
    "scripts.check_v5_api_contract",
    "scripts.smoke_v5",
)


def main() -> None:
    for module in CHECKS:
        print(f"[V5 acceptance] python -m {module}")
        subprocess.run([sys.executable, "-m", module], check=True)
    print(f"V5 acceptance passed: {len(CHECKS)} checks")


if __name__ == "__main__":
    main()
