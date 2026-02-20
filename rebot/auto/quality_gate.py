"""Quality gates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class QualityGate:
    root: Path

    def generate_ci(self) -> None:
        wf = self.root / ".github" / "workflows"
        wf.mkdir(parents=True, exist_ok=True)
        (wf / "ci.yml").write_text(
            "name: CI\n\non: [push, pull_request]\n\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: Setup Python\n        uses: actions/setup-python@v5\n        with:\n          python-version: '3.11'\n      - name: Install Python\n        run: |\n          if [ -f backend/requirements.txt ]; then pip install -r backend/requirements.txt; fi\n      - name: Install Node\n        uses: actions/setup-node@v4\n        with:\n          node-version: '20'\n      - name: Build Frontend\n        run: |\n          if [ -f frontend/package.json ]; then cd frontend && npm install && npm run build; fi\n      - name: Lint\n        run: echo \"lint placeholder\"\n      - name: Test\n        run: echo \"tests placeholder\"\n",
            encoding="utf-8",
        )
