from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    reason: str = "ok"


def evaluate_api_key(
    *,
    mode: str,
    expected: str,
    provided: str,
) -> AuthDecision:
    normalized_mode = (mode or "off").strip().lower()
    expected_key = (expected or "").strip()
    provided_key = (provided or "").strip()

    if normalized_mode in {"off", "disabled", "none"}:
        return AuthDecision(True, "off")
    if not expected_key:
        return AuthDecision(True, "no_expected_key")

    if normalized_mode == "compat":
        if provided_key and provided_key != expected_key:
            return AuthDecision(False, "invalid_api_key")
        return AuthDecision(True, "compat_allow")

    if normalized_mode == "enforce":
        if provided_key != expected_key:
            return AuthDecision(False, "unauthorized")
        return AuthDecision(True, "enforce_allow")

    return AuthDecision(True, "unknown_mode_allow")


def extract_api_key_from_headers(headers: Mapping[str, str]) -> str:
    direct = (headers.get("x-api-key") or headers.get("X-API-Key") or "").strip()
    if direct:
        return direct

    authz = (headers.get("authorization") or headers.get("Authorization") or "").strip()
    if authz.lower().startswith("bearer "):
        return authz[7:].strip()
    return ""
