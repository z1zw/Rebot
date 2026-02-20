from __future__ import annotations

from pathlib import Path

from app.intel.ast_index import ASTCodeIndexer


def test_ast_index_extracts_python_and_js_symbols(tmp_path: Path):
    (tmp_path / "main.py").write_text(
        "class C:\n    def m(self):\n        return 1\n\ndef fn():\n    return C()\n",
        encoding="utf-8",
    )
    (tmp_path / "main.js").write_text(
        "class D {}\nfunction run() { return D; }\n",
        encoding="utf-8",
    )
    idx = ASTCodeIndexer(tmp_path).build(include_references=True)
    names = {str(s.get('name')) for s in idx["symbols"]}
    assert "C" in names
    assert "m" in names
    assert "fn" in names
    assert "D" in names
    assert "run" in names


def test_ast_index_find_references(tmp_path: Path):
    (tmp_path / "u.py").write_text(
        "import math\n\ndef area(r):\n    return math.pi * r * r\n",
        encoding="utf-8",
    )
    out = ASTCodeIndexer(tmp_path).find_references(symbol="math")
    assert out["matches"] > 0
