from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from app.core.process_sandbox import popen_checked


def _spawn(cmd: list[str], env: dict[str, str]) -> subprocess.Popen:
    return popen_checked(
        cmd,
        allowed={"python", "py"},
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
        cwd=os.getcwd(),
    )


def main() -> int:
    port = os.getenv("REBOT_PORT", "8001")
    host = os.getenv("REBOT_HOST", "0.0.0.0")
    env = dict(os.environ)

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    embed_worker = os.getenv("EMBED_WORKER", "true").lower() in {"1", "true", "yes", "on"}
    force_local_tasks = os.getenv("FORCE_LOCAL_TASKS", "true").lower() in {"1", "true", "yes", "on"}
    use_external_worker = (not embed_worker) and (not force_local_tasks) and bool(os.getenv("RABBITMQ_URL"))

    print(f"Starting API on http://{host}:{port} ...")
    api = _spawn(api_cmd, env)
    children = [api]
    if use_external_worker:
        worker_cmd = [sys.executable, "-m", "app.worker"]
        print("Starting worker ...")
        worker = _spawn(worker_cmd, env)
        children.append(worker)
    try:
        while True:
            for p in children:
                code = p.poll()
                if code is not None:
                    print(f"Process exited: pid={p.pid} code={code}")
                    return code or 0
            time.sleep(0.8)
    except KeyboardInterrupt:
        print("Stopping processes ...")
        for p in children:
            try:
                p.send_signal(signal.SIGINT)
            except Exception:
                pass
        for p in children:
            try:
                p.wait(timeout=8)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
