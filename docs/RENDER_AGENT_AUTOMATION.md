# Render agent automation for Crypto Factory Studios

## Why this exists

Crypto Factory Studios already runs its FastAPI backend on Render and performs
substantial QA through GitHub Actions. Render Workflows is a better execution
surface for long-running, retryable runtime jobs because each task run gets
its own compute instance, timeout, retry boundary and observability instead of
blocking the web process.

Render Sandboxes are currently an Early Access capability. The repository
therefore treats them as an optional isolation boundary for agent-generated or
otherwise untrusted execution, never as part of the request path.

## Phase 1 — Workflows (ready to enable)

Entry point:

```text
python workflows/main.py
```

Dependencies:

```text
workflows/requirements.txt
```

Registered tasks:

- `backend_health` — checks Render `/health` and `/ready`.
- `edge_health` — checks the public Cloudflare edge.
- `repository_qa` — runs the fixed pytest suite with bounded runtime/output.
- `maintenance_cycle(include_qa=False)` — orchestrates health checks in
  parallel and optionally chains repository QA.

The workflow explicitly uses Render's `flex` compute plan. No task accepts an
arbitrary URL or arbitrary shell command.

### Recommended Render service settings

Create a **Workflow service** from this repository and use:

- Branch: `main`
- Build command: `pip install -r workflows/requirements.txt -r backend/requirements.txt`
- Start command: `python workflows/main.py`
- Root directory: repository root
- Secrets: none required for the health/QA tasks above

Do not add production database passwords, wallet secrets, private keys, payment
provider secrets or object-storage credentials unless a future task genuinely
needs them. Prefer task-specific credentials with the minimum possible scope.

## Phase 2 — Sandboxes (Early Access, opt-in only)

`workflows/sandbox_qa.py` provides a guarded helper for isolated QA.

Requirements:

- Render workspace has Sandboxes Early Access enabled.
- Trusted orchestrator has `RENDER_API_KEY` and `RENDER_WORKSPACE_ID`.
- The sandbox itself receives an empty environment.
- Only predefined suites may run.
- The sandbox is always terminated in a `finally` block.

Current predefined suites:

- `compile`
- `unit`

The helper intentionally does **not** accept arbitrary commands. That prevents
the task API from becoming a remote shell.

## Security model

Trusted zone:

- Render Workflow service
- Render API credential (only when Sandboxes are enabled)
- orchestration logic

Untrusted zone:

- ephemeral Sandbox instance
- copied source/tests only
- no application secrets
- bounded lifetime

Never copy `.env`, provider credentials, private keys, seed phrases, database
URLs, payment secrets or object-storage credentials into a sandbox.

## Suggested next migrations from GitHub Actions

Move work that is runtime-oriented rather than commit-oriented:

1. recurring production health sweeps;
2. controlled long-running QA;
3. archive/build validation after creator uploads;
4. background asset processing;
5. agent-assisted maintenance that produces a report before any write.

Keep commit gates, linting and pull-request checks in GitHub Actions.

## Rollout

1. Merge this scaffold.
2. Create the Render Workflow service.
3. Trigger `maintenance_cycle` manually and confirm task observability.
4. Enable a periodic trigger only after the manual run is clean.
5. Request/enable Sandboxes Early Access.
6. Test `run_isolated_suite("compile")` with no secrets.
7. Only then consider routing higher-risk generated-code QA through sandboxes.
