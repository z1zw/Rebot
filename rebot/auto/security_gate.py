"""Security gate for local attack testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SecurityGate:
    root: Path
    tools: list[str] = None

    def plan(self) -> list[str]:
        return [
            "nmap -sV -p- localhost",
            "zap-baseline.py -t http://localhost:8000",
            "pip-audit",
        ]

    def write_plan(self) -> None:
        (self.root / "SECURITY_PLAN.txt").write_text("\n".join(self.plan()), encoding="utf-8")

    def write_runner(self) -> None:
        (self.root / "run_security_tests.sh").write_text(
            "#!/usr/bin/env bash\nset -e\n" + "\n".join(self.plan()) + "\n",
            encoding="utf-8",
        )
