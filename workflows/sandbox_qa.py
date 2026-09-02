"""Early-access Render Sandbox helper for isolated CFS QA.

This module is deliberately not called by production code. It can be used only
after Sandboxes access is enabled for the Render workspace and the trusted
orchestrator has RENDER_API_KEY + RENDER_WORKSPACE_ID.

The sandbox receives no credentials. Only predefined commands can execute.
"""

from __future__ import annotations

from pathlib import Path

from render import RenderAsync
from render.experimental.sandbox import SandboxExecOutput

REPO_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_SUITES = {
    "compile": "python -m compileall -q backend workflows",
    "unit": "python -m pytest -q --disable-warnings --maxfail=1",
}


async def run_isolated_suite(suite: str) -> dict[str, object]:
    if suite not in ALLOWED_SUITES:
        raise ValueError(f"unsupported sandbox suite: {suite}")

    render = RenderAsync()
    sandboxes = render.experimental.sandboxes
    sandbox = await sandboxes.create(
        timeout_seconds=900,
        env={},
    )

    output_parts: list[str] = []
    exit_code: int | None = None
    try:
        # Copy only source required for QA. Secrets and local environment files
        # are not copied into the untrusted zone.
        for relative in ("backend", "workflows", "tests", "pytest.ini"):
            source = REPO_ROOT / relative
            if source.exists():
                await sandboxes.copy_to(sandbox.id, source, relative)

        command = (
            "python -m pip install -q -r backend/requirements.txt "
            "-r workflows/requirements.txt && " + ALLOWED_SUITES[suite]
        )
        async for event in sandboxes.exec(sandbox.id, command):
            if isinstance(event, SandboxExecOutput):
                output_parts.append(event.data)
            else:
                exit_code = event.exit_code

        output = "".join(output_parts)
        if len(output) > 12000:
            output = output[-12000:]

        return {
            "sandbox_id": sandbox.id,
            "suite": suite,
            "ok": exit_code == 0,
            "exit_code": exit_code,
            "output": output,
        }
    finally:
        await sandboxes.terminate(sandbox.id)
