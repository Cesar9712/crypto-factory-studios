"""Durable maintenance and QA tasks for Crypto Factory Studios.

These tasks are intentionally separated from the FastAPI web process so long-running
or retryable work cannot block production requests.

Security properties:
- No task accepts an arbitrary URL.
- No task accepts an arbitrary shell command.
- Health checks target only the known CFS production origins.
- QA executes a fixed command with bounded runtime and output.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from render import Retry, TaskContext, Workflows

BACKEND_ORIGIN = "https://crypto-factory-studios.onrender.com"
EDGE_ORIGIN = "https://crypto-factory-studios.cryptofactorystudios.workers.dev"
REPO_ROOT = Path(__file__).resolve().parents[1]

app = Workflows(
    default_retry=Retry(max_retries=2, wait_duration_ms=1500, backoff_scaling=2.0),
    default_timeout=600,
    default_plan="flex",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_url(url: str, *, timeout: float = 20.0) -> dict[str, object]:
    started = _utc_now()
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "cfs-render-workflows/1.0"},
    ) as client:
        response = client.get(url)
        return {
            "url": url,
            "status": response.status_code,
            "ok": 200 <= response.status_code < 400,
            "started_at": started,
            "finished_at": _utc_now(),
        }


@app.task(timeout_seconds=90)
def backend_health(ctx: TaskContext) -> dict[str, object]:
    """Verify the Render API health and readiness endpoints."""
    health = _check_url(f"{BACKEND_ORIGIN}/health")
    ready = _check_url(f"{BACKEND_ORIGIN}/ready")
    ok = bool(health["ok"]) and bool(ready["ok"])
    if not ok:
        raise RuntimeError(f"backend unhealthy: health={health} ready={ready}")
    return {"ok": True, "health": health, "ready": ready}


@app.task(timeout_seconds=90)
def edge_health(ctx: TaskContext) -> dict[str, object]:
    """Verify the Cloudflare edge can serve the public platform."""
    result = _check_url(EDGE_ORIGIN)
    if not result["ok"]:
        raise RuntimeError(f"edge unhealthy: {result}")
    return {"ok": True, "edge": result}


@app.task(
    timeout_seconds=1200,
    retry=Retry(max_retries=0, wait_duration_ms=1000),
)
def repository_qa(ctx: TaskContext) -> dict[str, object]:
    """Run the fixed repository test suite without accepting shell input."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--disable-warnings",
        "--maxfail=1",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1100,
        check=False,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    # Keep task state compact; Render persists task results temporarily.
    if len(output) > 12000:
        output = output[-12000:]

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": command,
        "output": output,
        "finished_at": _utc_now(),
    }


@app.task(timeout_seconds=1500)
async def maintenance_cycle(ctx: TaskContext, include_qa: bool = False) -> dict[str, object]:
    """Run independent platform checks in parallel and optional repository QA."""
    backend_result, edge_result = await asyncio.gather(
        ctx.run(backend_health),
        ctx.run(edge_health),
    )

    result: dict[str, object] = {
        "ok": True,
        "backend": backend_result,
        "edge": edge_result,
        "finished_at": _utc_now(),
    }

    if include_qa:
        qa_result = await ctx.run(repository_qa)
        result["qa"] = qa_result
        result["ok"] = bool(qa_result["ok"])

    return result


if __name__ == "__main__":
    app.start()
