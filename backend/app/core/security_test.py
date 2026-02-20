from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import asyncio
import shutil
from urllib.parse import urlparse

from app.core.process_sandbox import run_checked


@dataclass
class SecurityTestResult:
    tool: str
    ok: bool
    output: str


def _is_local_target(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return host in {"localhost", "127.0.0.1"}


async def run_security_tests(
    *, target_url: str, tools: list[str]
) -> list[SecurityTestResult]:
    if not _is_local_target(target_url):
        return [
            SecurityTestResult(
                tool="guard",
                ok=False,
                output="Target must be localhost or 127.0.0.1",
            )
        ]
    results: list[SecurityTestResult] = []
    for tool in tools:
        if tool == "zap":
            exe = shutil.which("zap-baseline.py")
            if not exe:
                results.append(
                    SecurityTestResult(
                        tool="zap",
                        ok=False,
                        output="zap-baseline.py not found in PATH",
                    )
                )
                continue
            cmd = [exe, "-t", target_url, "-I"]
        elif tool == "nuclei":
            exe = shutil.which("nuclei")
            if not exe:
                results.append(
                    SecurityTestResult(
                        tool="nuclei",
                        ok=False,
                        output="nuclei not found in PATH",
                    )
                )
                continue
            cmd = [exe, "-u", target_url, "-silent"]
        else:
            results.append(SecurityTestResult(tool=tool, ok=False, output="Unknown tool"))
            continue
        output = await _run_cmd(cmd)
        results.append(SecurityTestResult(tool=tool, ok=True, output=output))
    return results


async def _run_cmd(cmd: list[str]) -> str:
    def _run() -> str:
        completed = run_checked(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return f"exit={completed.returncode}\n{completed.stdout}\n{completed.stderr}"

    return await asyncio.to_thread(_run)
