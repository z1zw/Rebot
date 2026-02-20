from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib import error as urllib_error, request as urllib_request
from urllib.parse import urljoin, urlparse


def probe_preview_url(url: str) -> dict[str, Any]:
    u = (url or "").strip()
    if not u:
        return {"healthy": False, "reason": "empty_url"}
    try:
        req = urllib_request.Request(u, method="GET")
        with urllib_request.urlopen(req, timeout=2) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 200))
            raw_body = resp.read(1024 * 64).decode("utf-8", errors="ignore")
            body = raw_body.lower()
            if status >= 400:
                return {"healthy": False, "reason": f"http_{status}", "status_code": status}
            if "404 not found" in body or "cannot get /" in body or "<title>404" in body:
                return {"healthy": False, "reason": "http_404_body", "status_code": status}
            asset_probe = _probe_static_assets(url=u, html=raw_body)
            if not asset_probe["healthy"]:
                failed = asset_probe.get("failed_assets") or []
                return {
                    "healthy": False,
                    "reason": "asset_unreachable",
                    "status_code": status,
                    "failed_assets": failed[:8],
                }
            return {"healthy": True, "reason": "ok", "status_code": status}
    except urllib_error.HTTPError as exc:
        return {"healthy": False, "reason": f"http_{exc.code}", "status_code": int(exc.code)}
    except urllib_error.URLError as exc:
        reason = str(exc.reason).lower()
        if "refused" in reason:
            return {"healthy": False, "reason": "connection_refused"}
        if "timed out" in reason or "timeout" in reason:
            return {"healthy": False, "reason": "timeout"}
        if "name or service not known" in reason or "nodename nor servname provided" in reason:
            return {"healthy": False, "reason": "dns_error"}
        return {"healthy": False, "reason": f"url_error:{reason}"}
    except Exception as exc:  # noqa: BLE001
        return {"healthy": False, "reason": f"error:{exc}"}


def _probe_static_assets(url: str, html: str) -> dict[str, Any]:
    try:
        base = urlparse(url)
        base_host = (base.netloc or "").lower()
        refs = set()
        refs.update(re.findall(r"""<script[^>]+src\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE))
        refs.update(re.findall(r"""<link[^>]+href\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE))
        refs.update(re.findall(r"""<img[^>]+src\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE))
        candidates = []
        for ref in refs:
            s = (ref or "").strip()
            if not s or s.startswith("#") or s.startswith("data:") or s.startswith("javascript:"):
                continue
            full = urljoin(url, s)
            parsed = urlparse(full)
            target_host = (parsed.netloc or "").lower()
            if target_host and base_host and target_host != base_host:
                # External CDN/network assets should not decide local preview health.
                continue
            if full not in candidates:
                candidates.append(full)
        sample = candidates[:10]
        failed: list[str] = []
        for asset in sample:
            req = urllib_request.Request(asset, method="GET")
            try:
                with urllib_request.urlopen(req, timeout=2) as resp:  # noqa: S310
                    code = int(getattr(resp, "status", 200))
                    if code >= 400:
                        failed.append(f"{asset} ({code})")
            except Exception:
                failed.append(asset)
        return {"healthy": len(failed) == 0, "failed_assets": failed}
    except Exception:
        return {"healthy": True, "failed_assets": []}


async def await_preview_health(url: str, retries: int = 6, delay: float = 0.4) -> dict[str, Any]:
    if not url:
        return {"healthy": False, "reason": "empty_url"}
    loop = asyncio.get_running_loop()
    last: dict[str, Any] = {"healthy": False, "reason": "unknown"}
    for _ in range(retries):
        health = await loop.run_in_executor(None, probe_preview_url, url)
        last = health
        if health.get("healthy"):
            return health
        await asyncio.sleep(delay)
    return last
