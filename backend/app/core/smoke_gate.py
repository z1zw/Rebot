from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import shutil

from app.core.process_sandbox import run_checked


def _cp_result(ok: bool, name: str, returncode: int, stderr: str = "", stdout: str = "", blocking: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "returncode": int(returncode),
        "stderr": (stderr or "")[-1200:],
        "stdout": (stdout or "")[-1200:],
        "blocking": bool(blocking),
    }


def run_framework_smoke_check(*, workspace: Path, framework: str) -> dict[str, Any]:
    fw = (framework or "html").strip().lower()
    root = workspace.resolve()
    checks: list[dict[str, Any]] = []
    blocking_issues: list[str] = []

    def _run(cmd: list[str], name: str, timeout_s: int = 180, blocking: bool = True) -> None:
        try:
            cp = run_checked(cmd, cwd=root, timeout=timeout_s, capture_output=True, text=True)
            ok = cp.returncode == 0
            checks.append(_cp_result(ok, name, cp.returncode, cp.stderr or "", cp.stdout or "", blocking=blocking))
            if (not ok) and blocking:
                blocking_issues.append(f"{name}: rc={cp.returncode}")
        except Exception as exc:
            checks.append(_cp_result(False, name, 1, str(exc), "", blocking=blocking))
            if blocking:
                blocking_issues.append(f"{name}: {exc}")

    def _require(path: Path, name: str) -> None:
        ok = path.exists()
        checks.append(_cp_result(ok, name, 0 if ok else 1, "" if ok else f"missing {path.name}", "", blocking=True))
        if not ok:
            blocking_issues.append(name)

    if fw == "flutter":
        _require(root / "pubspec.yaml", "entry:pubspec_yaml")
        _require(root / "lib" / "main.dart", "entry:lib_main_dart")
        if shutil.which("flutter") or shutil.which("flutter.bat"):
            _run(["flutter", "--version"], "flutter:version", timeout_s=45)
            _run(["flutter", "analyze"], "flutter:analyze", timeout_s=240)
        else:
            checks.append(_cp_result(False, "flutter:sdk_present", 1, "flutter executable not found", "", blocking=True))
            blocking_issues.append("flutter:sdk_present")

    elif fw in {"react", "vue", "nextjs", "uniapp"}:
        pkg = root / "package.json"
        _require(pkg, "entry:package_json")
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                has_build = isinstance(data, dict) and isinstance(data.get("scripts"), dict) and "build" in data.get("scripts", {})
                checks.append(_cp_result(True, "pkg:parse", 0, "", "", blocking=False))
            except Exception as exc:
                has_build = False
                checks.append(_cp_result(False, "pkg:parse", 1, str(exc), "", blocking=True))
                blocking_issues.append("pkg:parse")
            if shutil.which("node") and (shutil.which("npm") or shutil.which("npm.cmd")):
                _run(["node", "--version"], "node:version", timeout_s=25)
                if has_build:
                    _run(["npm", "run", "build"], "npm:build", timeout_s=360)
                else:
                    checks.append(_cp_result(True, "npm:build_skipped_no_script", 0, "", "", blocking=False))
            else:
                checks.append(_cp_result(False, "node:npm_present", 1, "node/npm executable not found", "", blocking=True))
                blocking_issues.append("node:npm_present")

    elif fw == "python":
        py_files = [p for p in root.rglob("*.py") if p.is_file()]
        if not py_files:
            checks.append(_cp_result(False, "python:files_present", 1, "no python files found", "", blocking=True))
            blocking_issues.append("python:files_present")
        _run(["python", "-m", "compileall", "-q", "."], "python:compileall", timeout_s=180)

    elif fw == "html":
        _require(root / "index.html", "entry:index_html")
        js_files = [p for p in root.rglob("*.js") if p.is_file()]
        if js_files:
            if shutil.which("node"):
                for p in js_files[:20]:
                    rel = p.relative_to(root).as_posix()
                    _run(["node", "--check", rel], f"node:check:{rel}", timeout_s=35)
            else:
                checks.append(_cp_result(False, "node:present_for_js_check", 1, "node executable not found", "", blocking=True))
                blocking_issues.append("node:present_for_js_check")

    else:
        checks.append(_cp_result(True, "generic:skip", 0, "", "", blocking=False))

    ok = len(blocking_issues) == 0
    summary = "ok" if ok else f"failed:{'; '.join(blocking_issues[:6])}"
    return {"ok": ok, "framework": fw, "summary": summary, "checks": checks, "blocking_issues": blocking_issues}
