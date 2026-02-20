from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re


@dataclass
class RepoSymbol:
    path: str
    kind: str
    name: str
    line: int


class RepoMapBuilder:
    def __init__(
        self,
        root: Path,
        *,
        max_files: int = 300,
        max_symbols_per_file: int = 80,
    ) -> None:
        self.root = root.resolve()
        self.max_files = max_files
        self.max_symbols_per_file = max_symbols_per_file

    def build(self) -> dict[str, Any]:
        files = self._collect_files()
        symbols: list[RepoSymbol] = []
        for file_path in files:
            try:
                symbols.extend(self._extract_symbols(file_path))
            except Exception:
                continue
        return {
            "workspace": str(self.root),
            "file_count": len(files),
            "files": [self._rel(p) for p in files],
            "symbols": [s.__dict__ for s in symbols],
        }

    def to_compact_text(self, repo_map: dict[str, Any], max_chars: int = 12000) -> str:
        lines: list[str] = []
        lines.append(f"<repo_map root=\"{repo_map.get('workspace', '')}\">")
        for p in repo_map.get("files", []):
            lines.append(f"  <file path=\"{p}\"/>")
        for sym in repo_map.get("symbols", []):
            lines.append(
                "  <symbol path=\"{path}\" kind=\"{kind}\" line=\"{line}\">{name}</symbol>".format(
                    path=sym.get("path", ""),
                    kind=sym.get("kind", ""),
                    line=sym.get("line", 0),
                    name=(sym.get("name", "") or "").replace("<", "").replace(">", ""),
                )
            )
        lines.append("</repo_map>")
        out = "\n".join(lines)
        if len(out) > max_chars:
            return out[:max_chars]
        return out

    def _collect_files(self) -> list[Path]:
        out: list[Path] = []
        allowed = {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".dart",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cs",
            ".html",
            ".css",
            ".json",
            ".yaml",
            ".yml",
            ".md",
        }
        for p in self.root.rglob("*"):
            if len(out) >= self.max_files:
                break
            if not p.is_file():
                continue
            if any(part in {".git", ".venv", "node_modules", "build", "dist", "__pycache__"} for part in p.parts):
                continue
            if p.suffix.lower() not in allowed:
                continue
            out.append(p)
        return out

    def _extract_symbols(self, file_path: Path) -> list[RepoSymbol]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        ext = file_path.suffix.lower()
        rel = self._rel(file_path)
        symbols: list[RepoSymbol] = []

        # Tree-sitter optional fast path.
        try:
            symbols = self._extract_symbols_tree_sitter(rel, ext, text)
            if symbols:
                return symbols[: self.max_symbols_per_file]
        except Exception:
            pass

        patterns: list[tuple[str, str]] = []
        if ext in {".py"}:
            patterns = [
                (r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", "class"),
                (r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            ]
        elif ext in {".js", ".ts", ".jsx", ".tsx"}:
            patterns = [
                (r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", "class"),
                (r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
                (r"^\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(", "function"),
            ]
        elif ext in {".dart"}:
            patterns = [
                (r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", "class"),
                (r"^\s*(?:Future<.*?>\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            ]
        elif ext in {".go"}:
            patterns = [
                (r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+struct", "struct"),
                (r"^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", "function"),
            ]

        if not patterns:
            return []

        for i, line in enumerate(text.splitlines(), start=1):
            for pattern, kind in patterns:
                m = re.search(pattern, line)
                if m:
                    symbols.append(RepoSymbol(path=rel, kind=kind, name=m.group(1), line=i))
                    if len(symbols) >= self.max_symbols_per_file:
                        return symbols
                    break
        return symbols

    def _extract_symbols_tree_sitter(self, rel: str, ext: str, text: str) -> list[RepoSymbol]:
        from tree_sitter_languages import get_parser  # type: ignore

        lang_by_ext = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
        }
        lang = lang_by_ext.get(ext)
        if not lang:
            return []
        parser = get_parser(lang)
        tree = parser.parse(text.encode("utf-8", errors="ignore"))
        root = tree.root_node
        out: list[RepoSymbol] = []
        stack = [root]
        capture = {
            "class_definition": "class",
            "function_definition": "function",
            "method_definition": "method",
            "function_declaration": "function",
            "class_declaration": "class",
            "struct_item": "struct",
        }
        while stack:
            node = stack.pop()
            kind = capture.get(node.type)
            if kind:
                name = self._extract_node_name(node, text)
                if name:
                    out.append(
                        RepoSymbol(
                            path=rel,
                            kind=kind,
                            name=name,
                            line=int(node.start_point[0]) + 1,
                        )
                    )
                    if len(out) >= self.max_symbols_per_file:
                        break
            for ch in node.children:
                stack.append(ch)
        return out

    def _extract_node_name(self, node: Any, text: str) -> str:
        for ch in node.children:
            if ch.type in {"identifier", "type_identifier", "name"}:
                return text[ch.start_byte : ch.end_byte].strip()
        return ""

    def _rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root)).replace("\\", "/")
        except Exception:
            return p.name

