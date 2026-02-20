from __future__ import annotations

import asyncio
from typing import Any
from urllib import error as urllib_error, request as urllib_request


def probe_preview_url(url: str) -> dict[str, Any]:
    u = (url or "").strip()
    if not u:
        return {"healthy": False, "reason": "empty_url"}
    try:
        req = urllib_request.Request(u, method="GET")
        with urllib_request.urlopen(req, timeout=2) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 200))
            body = resp.read(1024 * 8).decode("utf-8", errors="ignore").lower()
            if status >= 400:
                return {"healthy": False, "reason": f"http_{status}", "status_code": status}
            if "404 not found" in body or "cannot get /" in body or "<title>404" in body:
                return {"healthy": False, "reason": "http_404_body", "status_code": status}
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
