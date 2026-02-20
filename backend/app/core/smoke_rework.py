from __future__ import annotations

from typing import Any


def _norm_framework(framework: str) -> str:
    fw = (framework or "").strip().lower()
    if fw in {"", "general"}:
        return "html"
    return fw


def _to_lines(blocking_issues: list[Any] | None) -> list[str]:
    out: list[str] = []
    for item in (blocking_issues or []):
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def detect_environment_blockers(blocking_issues: list[Any] | None) -> list[str]:
    lines = _to_lines(blocking_issues)
    keys = (
        "node:npm_present",
        "node:present_for_js_check",
        "flutter:sdk_present",
    )
    out: list[str] = []
    for line in lines:
        low = line.lower()
        if any(k in low for k in keys):
            out.append(line)
    return out


def _classify_issue(line: str) -> str:
    low = line.lower()
    if low.startswith("entry:"):
        return "entrypoint"
    if low.startswith("dom_audit:"):
        return "dom_binding"
    if low.startswith("node:check:"):
        return "js_syntax"
    if low.startswith("npm:build"):
        return "build"
    if low.startswith("flutter:analyze"):
        return "analyze"
    if low.startswith("python:compileall"):
        return "python_compile"
    if "sdk_present" in low or "npm_present" in low:
        return "environment"
    return "runtime"


def _framework_rules(framework: str) -> list[str]:
    fw = _norm_framework(framework)
    if fw == "html":
        return [
            "Keep index.html as root entry and ensure script/style paths are relative and existing.",
            "Fix all JS syntax errors and ensure runtime event handlers are attached to existing DOM ids.",
            "Implement fully interactive gameplay; no static-only output.",
            "Use a strong visual system with CSS variables, gradients, cards, and consistent spacing.",
            "Avoid plain white default page and browser-default typography.",
        ]
    if fw in {"react", "vue", "nextjs", "uniapp"}:
        return [
            "Fix compile/build errors so npm run build succeeds.",
            "Keep framework-correct project structure and valid imports.",
            "Implement complete interaction handlers and state updates.",
            "Define design tokens (colors/spacing/radius/typography) and polished layout hierarchy.",
            "Avoid unstyled white screens or placeholder-only pages.",
        ]
    if fw == "flutter":
        return [
            "Fix flutter analyze errors, including unresolved types/imports and invalid widget parameters.",
            "Ensure pubspec.yaml and lib/main.dart remain runnable.",
            "Keep all referenced classes defined or imported.",
            "Use polished UI tokens and adaptive layouts (not plain default material page).",
        ]
    if fw == "python":
        return [
            "Fix python compile errors and syntax issues for all .py files.",
            "Ensure main entry can run and complete primary user flow.",
            "Provide styled terminal or web output where applicable, not placeholder text.",
        ]
    return [
        "Fix all runtime blocking issues and keep project runnable.",
        "Keep full interaction and non-placeholder delivery.",
    ]


def _issue_hints(blocking_issues: list[str]) -> list[str]:
    hints: list[str] = []
    for line in blocking_issues[:20]:
        cls = _classify_issue(line)
        if cls == "entrypoint":
            hints.append(f"{line} => create/fix required entry file and wire startup path")
        elif cls == "dom_binding":
            hints.append(f"{line} => ensure all referenced DOM ids exist and event handlers bind after DOM ready")
        elif cls == "js_syntax":
            hints.append(f"{line} => fix syntax/module errors in the target js file")
        elif cls == "build":
            hints.append(f"{line} => resolve compile/import/type errors to make build pass")
        elif cls == "analyze":
            hints.append(f"{line} => fix flutter analyzer diagnostics and invalid widget signatures")
        elif cls == "python_compile":
            hints.append(f"{line} => fix python syntax/import errors")
        elif cls == "environment":
            hints.append(f"{line} => environment missing runtime dependency; do not retry code-only fix")
        else:
            hints.append(f"{line} => inspect and fix runtime blocker directly")
    return hints


def build_smoke_rework_task(
    *,
    base_task: str,
    framework: str,
    blocking_issues: list[Any] | None,
    attempt: int,
    budget: int,
    is_game: bool,
) -> str:
    issues = _to_lines(blocking_issues)
    issue_block = "\n".join(f"- {x}" for x in issues) if issues else "- unknown runtime failure"
    hint_lines = _issue_hints(issues)
    hints = "\n".join(f"- {x}" for x in hint_lines) if hint_lines else "- fix all blocking runtime issues"
    fw_rules = "\n".join(f"- {x}" for x in _framework_rules(framework))
    game_rules = ""
    if is_game:
        game_rules = (
            "- Deliver a production-quality game visual style: strong color palette, non-flat background, clear HUD, polished controls.\n"
            "- Keep complete game loop and interaction: start/pause/restart, score updates, win/lose states.\n"
            "- Ensure gameplay is interactive immediately after run, not static narrative text.\n"
        )
    return (
        f"{(base_task or '').strip()}\n\n"
        "RUNTIME_SMOKE_FAILURES\n"
        f"{issue_block}\n\n"
        "FAILURE_HINTS\n"
        f"{hints}\n\n"
        "REPAIR_STRATEGY\n"
        f"- attempt={attempt}/{max(1, budget)}\n"
        f"- framework={_norm_framework(framework)}\n"
        "- Return complete runnable files only.\n"
        "- Do not output pseudo-code or TODO placeholders.\n"
        "- Keep IDs/imports/types consistent across files.\n"
        f"{game_rules}"
        "FRAMEWORK_REQUIREMENTS\n"
        f"{fw_rules}\n"
    )

