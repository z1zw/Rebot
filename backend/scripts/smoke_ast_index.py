from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.intel.ast_index import ASTCodeIndexer


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text(
            "import os\n\nclass A:\n    def f(self):\n        return os.getcwd()\n\ndef g(x):\n    return f'{x}'\n",
            encoding="utf-8",
        )
        (root / "b.js").write_text(
            "import { useState } from 'react';\nclass B {}\nfunction h() { return useState; }\nconst z = () => h();\n",
            encoding="utf-8",
        )

        indexer = ASTCodeIndexer(root)
        idx = indexer.build(include_references=True)
        _assert(int(idx.get("file_count", 0)) == 2, f"unexpected file_count: {idx.get('file_count')}")
        symbols = idx.get("symbols", [])
        names = {str(s.get("name")) for s in symbols}
        _assert("A" in names and "f" in names and "g" in names and "B" in names and "h" in names, f"missing symbols: {names}")

        refs = indexer.find_references(symbol="useState")
        _assert(int(refs.get("matches", 0)) > 0, "expected references for useState")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"[FAIL] ast index smoke failed: {exc}")
        sys.exit(1)
    print("[OK] ast index smoke passed")
