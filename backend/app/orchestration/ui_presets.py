from __future__ import annotations

from typing import Any


_PRESETS: dict[str, dict[str, Any]] = {
    "cursor_ide": {
        "name": "cursor_ide",
        "desc": "Dense professional IDE look with restrained contrast and focused spacing.",
        "rules": [
            "Use compact spacing and clear hierarchy for desktop.",
            "Prefer subtle surfaces (#F9F9FB, #F2F2F5, #EAECF0) over pure white blocks.",
            "Use modern sans typography and clear 13/14/16 scale.",
            "Avoid visual noise and giant banners.",
        ],
    },
    "tismart_xcode": {
        "name": "tismart_xcode",
        "desc": "Xcode-like toolbar density and panel segmentation.",
        "rules": [
            "Toolbar should be compact and information-dense.",
            "Use segmented controls for top-right tool switches.",
            "Use light separators and restrained shadows.",
            "Keep panel identities distinct with subtle background differences.",
        ],
    },
    "mgx_card": {
        "name": "mgx_card",
        "desc": "Agent-card communication style with structured step cards.",
        "rules": [
            "Use clear agent role labels and step progression blocks.",
            "Prefer readable line-height and consistent card radius.",
            "Use status chips sparingly and semantically.",
            "Make generated system actions full-width and obvious.",
        ],
    },
    "arcade_game": {
        "name": "arcade_game",
        "desc": "Production-ready arcade game visual language with rich color and high contrast gameplay HUD.",
        "rules": [
            "Define a full design token system (colors, spacing, radius, shadow, typography) via CSS variables or theme constants.",
            "Avoid plain white backgrounds; use layered gradients or atmospheric surfaces.",
            "Provide strong visual hierarchy: title, HUD, game board, controls, status overlays.",
            "Use vivid but coherent palette with readable contrast and consistent button styles.",
            "Include hover/active/disabled states and transition polish for controls.",
            "For web games, ensure board/canvas has clear frame and responsive scaling.",
        ],
    },
}


def choose_ui_preset(task: str, framework: str) -> dict[str, Any]:
    t = (task or "").lower()
    fw = (framework or "").lower()
    if any(k in t for k in ("game", "arcade", "maze", "runner", "puzzle", "cheese")):
        key = "arcade_game"
    elif any(k in t for k in ("xcode", "tismart", "ide", "toolbar", "desktop")):
        key = "tismart_xcode"
    elif any(k in t for k in ("agent", "workflow", "card", "mgx")):
        key = "mgx_card"
    elif fw in {"flutter", "react", "nextjs", "uniapp", "html"}:
        key = "cursor_ide"
    else:
        key = "cursor_ide"
    return _PRESETS[key]
