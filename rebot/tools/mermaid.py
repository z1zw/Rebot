"""Mermaid rendering helpers."""

from __future__ import annotations

import base64
from pathlib import Path
import httpx


def render_mermaid_png(mermaid_text: str, output_path: Path, mermaid_ink_url: str) -> None:
    data = mermaid_text.encode("utf-8")
    encoded = base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")
    url = mermaid_ink_url.rstrip("/") + f"/img/{encoded}"
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url)
    resp.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)
