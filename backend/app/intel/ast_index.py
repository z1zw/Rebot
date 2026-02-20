from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PY_EXTS = {".py"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx"}
CODE_EXTS = PY_EXTS | JS_EXTS
SKIP_DIRS = {".git", ".venv", "node_modules", "build", "dist", "__pycache__", ".rebot"}


@dataclass
class IndexedSymbol:
    path: str
    language: str
    kind: str
    name: str
    line: int
    scope: str


@dataclass
class SymbolReference:
    path: str
    language: str
    name: str
    line: int
    context: str


class ASTCodeIndexer:
    def __init__(
        self,
        root: Path,
        *,
        max_files: int = 300,
        max_file_bytes: int = 512_000,
        max_symbols_per_file: int = 400,
        max_refs_per_file: int = 1500,
    ) -> None:
        self.root = root.resolve()
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_symbols_per_file = max_symbols_per_file
        self.max_refs_per_file = max_refs_per_file

    def build(self, *, include_references: bool = True) -> dict[str, Any]:
        files = self._collect_files()
        symbols: list[IndexedSymbol] = []
        refs: list[SymbolReference] = []
        skipped: list[str] = []
        for p in files:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                skipped.append(self._rel(p))
                continue
            if len(text.encode("utf-8", errors="ignore")) > self.max_file_bytes:
                skipped.append(self._rel(p))
                continue
            ext = p.suffix.lower()
            if ext in PY_EXTS:
                file_symbols, file_refs = self._analyze_python(p, text)
            elif ext in JS_EXTS:
                file_symbols, file_refs = self._analyze_jsts(p, text)
            else:
                continue
            symbols.extend(file_symbols[: self.max_symbols_per_file])
            if include_references:
                refs.extend(file_refs[: self.max_refs_per_file])
        return {
            "workspace": str(self.root),
            "file_count": len(files),
            "files": [self._rel(p) for p in files],
            "skipped_files": skipped,
            "symbol_count": len(symbols),
            "reference_count": len(refs),
            "symbols": [s.__dict__ for s in symbols],
            "references": [r.__dict__ for r in refs],
        }

    def find_references(self, *, symbol: str, include_definitions: bool = True) -> dict[str, Any]:
        target = (symbol or "").strip()
        if not target:
            raise ValueError("symbol required")
        idx = self.build(include_references=True)
        refs = [r for r in idx["references"] if str(r.get("name") or "") == target]
        defs: list[dict[str, Any]] = []
        if include_definitions:
            defs = [s for s in idx["symbols"] if str(s.get("name") or "") == target]
        return {
            "workspace": idx["workspace"],
            "symbol": target,
            "matches": len(refs) + len(defs),
            "definitions": defs,
            "references": refs,
        }

    def to_compact_text(
        self,
        index: dict[str, Any],
        *,
        max_chars: int = 12000,
        max_symbols: int = 300,
        max_refs: int = 500,
    ) -> str:
        lines: list[str] = []
        lines.append(f"<ast_index root=\"{index.get('workspace', '')}\">")
        lines.append(
            f"  <stats files=\"{index.get('file_count', 0)}\" symbols=\"{index.get('symbol_count', 0)}\" refs=\"{index.get('reference_count', 0)}\"/>"
        )
        for sym in (index.get("symbols") or [])[: max(1, int(max_symbols))]:
            lines.append(
                "  <symbol path=\"{path}\" lang=\"{lang}\" kind=\"{kind}\" line=\"{line}\" scope=\"{scope}\">{name}</symbol>".format(
                    path=sym.get("path", ""),
                    lang=sym.get("language", ""),
                    kind=sym.get("kind", ""),
                    line=sym.get("line", 0),
                    scope=(str(sym.get("scope", "")) or "").replace('"', "'"),
                    name=(str(sym.get("name", "")) or "").replace("<", "").replace(">", ""),
                )
            )
        for ref in (index.get("references") or [])[: max(1, int(max_refs))]:
            lines.append(
                "  <ref path=\"{path}\" lang=\"{lang}\" line=\"{line}\" context=\"{context}\">{name}</ref>".format(
                    path=ref.get("path", ""),
                    lang=ref.get("language", ""),
                    line=ref.get("line", 0),
                    context=(str(ref.get("context", "")) or "").replace('"', "'"),
                    name=(str(ref.get("name", "")) or "").replace("<", "").replace(">", ""),
                )
            )
        lines.append("</ast_index>")
        out = "\n".join(lines)
        return out[:max_chars] if len(out) > max_chars else out

    def _collect_files(self) -> list[Path]:
        out: list[Path] = []
        for p in self.root.rglob("*"):
            if len(out) >= self.max_files:
                break
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() not in CODE_EXTS:
                continue
            out.append(p)
        return out

    def _analyze_python(self, file_path: Path, text: str) -> tuple[list[IndexedSymbol], list[SymbolReference]]:
        rel = self._rel(file_path)
        symbols: list[IndexedSymbol] = []
        refs: list[SymbolReference] = []

        class Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.scope_stack: list[str] = []

            def _scope(self) -> str:
                return ".".join(self.scope_stack) if self.scope_stack else "<module>"

            def visit_ClassDef(self, node: ast.ClassDef) -> Any:
                symbols.append(
                    IndexedSymbol(
                        path=rel,
                        language="python",
                        kind="class",
                        name=node.name,
                        line=int(node.lineno),
                        scope=self._scope(),
                    )
                )
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
                symbols.append(
                    IndexedSymbol(
                        path=rel,
                        language="python",
                        kind="function",
                        name=node.name,
                        line=int(node.lineno),
                        scope=self._scope(),
                    )
                )
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
                symbols.append(
                    IndexedSymbol(
                        path=rel,
                        language="python",
                        kind="async_function",
                        name=node.name,
                        line=int(node.lineno),
                        scope=self._scope(),
                    )
                )
                self.scope_stack.append(node.name)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_Name(self, node: ast.Name) -> Any:
                if isinstance(node.ctx, ast.Load):
                    refs.append(
                        SymbolReference(
                            path=rel,
                            language="python",
                            name=node.id,
                            line=int(node.lineno),
                            context=self._scope(),
                        )
                    )
                self.generic_visit(node)

            def visit_Import(self, node: ast.Import) -> Any:
                for alias in node.names:
                    refs.append(
                        SymbolReference(
                            path=rel,
                            language="python",
                            name=(alias.asname or alias.name.split(".")[0]),
                            line=int(node.lineno),
                            context=self._scope(),
                        )
                    )

            def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
                for alias in node.names:
                    refs.append(
                        SymbolReference(
                            path=rel,
                            language="python",
                            name=(alias.asname or alias.name),
                            line=int(node.lineno),
                            context=self._scope(),
                        )
                    )

        try:
            tree = ast.parse(text)
            Visitor().visit(tree)
        except Exception:
            return self._analyze_jsts(file_path, text)
        return symbols, refs

    def _analyze_jsts(self, file_path: Path, text: str) -> tuple[list[IndexedSymbol], list[SymbolReference]]:
        rel = self._rel(file_path)
        symbols: list[IndexedSymbol] = []
        refs: list[SymbolReference] = []
        lines = text.splitlines()
        patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(r"^\s*class\s+([A-Za-z_$][A-Za-z0-9_$]*)"), "class"),
            (re.compile(r"^\s*function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\("), "function"),
            (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\("), "function"),
            (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?[A-Za-z_$][A-Za-z0-9_$]*\s*=>"), "function"),
        ]
        ident_re = re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*\b")
        js_kw = {
            "if", "else", "return", "new", "class", "function", "const", "let", "var", "export", "import", "from",
            "await", "async", "for", "while", "switch", "case", "break", "continue", "try", "catch", "finally",
            "throw", "typeof", "instanceof", "void", "null", "undefined", "true", "false", "this", "super", "default",
        }
        for i, line in enumerate(lines, start=1):
            for pat, kind in patterns:
                m = pat.search(line)
                if m:
                    symbols.append(
                        IndexedSymbol(
                            path=rel,
                            language="javascript",
                            kind=kind,
                            name=m.group(1),
                            line=i,
                            scope="<module>",
                        )
                    )
                    break
            for m in ident_re.finditer(line):
                token = m.group(0)
                if token in js_kw:
                    continue
                refs.append(
                    SymbolReference(
                        path=rel,
                        language="javascript",
                        name=token,
                        line=i,
                        context="<module>",
                    )
                )
        return symbols, refs

    def _rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root)).replace("\\", "/")
        except Exception:
            return p.name
