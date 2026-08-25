# Crypto Factory Studios — Production Creator Platform

Crypto Factory Studios is a security-first Web game publishing platform for players and creators. The current release runs with a FastAPI backend on Render, persistent PostgreSQL on Neon, private S3-compatible object storage on Backblaze B2, and a Cloudflare Worker serving the frontend and proxying API/play traffic.

## Verified platform capabilities

- Player registration, login, logout, logout-all and account deletion.
- HttpOnly production session cookies with CSRF protection.
- Creator activation and server-side Free / Plus / Pro plan limits.
- Internal owner account support with `internal_unlimited` and `billing_exempt`.
- Creator game creation, editing, secure ZIP upload, quarantine/scan gating, publishing, unpublishing and deletion.
- Persistent build archives and published assets in S3-compatible object storage.
- Public catalog, game detail pages and `/play/{slug}/` delivery.
- Published-game CSP sandbox isolation from platform credentials.
- Per-user cloud saves with optimistic revision conflict detection.
- Reports, moderation, audit logs and administrative endpoints.
- Server-authoritative products, quotes, orders, anti-replay/idempotency and purchase history for payment TEST/MOCK flows.
- PostgreSQL compatibility tests plus disposable production E2E verification.

## Production architecture

```text
Browser
  ↓
Cloudflare Worker / static assets
  ↓
Render FastAPI backend
  ├── Neon PostgreSQL       (persistent structured data)
  └── Backblaze B2 / S3     (persistent archives and published game assets)
```

Render Free has an ephemeral filesystem. Production therefore refuses to run without `DATABASE_URL` and S3-compatible persistent storage. Local filesystem storage remains development/test only.

## Upload security

Every build is structurally validated before publication. The built-in low-memory scanner rejects dangerous archive structures such as traversal paths, encrypted entries, normalized duplicate paths, symlinks, disallowed file types, excessive archive expansion and suspicious compression ratios, and includes static EICAR detection. Render Free uses this built-in scanner by default. An external antivirus can be made mandatory explicitly with `CFS_EXTERNAL_ANTIVIRUS_REQUIRED=true` only when a compatible external scanner is actually available.

Published creator content is treated as untrusted and served with CSP sandbox isolation. The sandbox intentionally omits `allow-same-origin` so uploaded JavaScript cannot inherit the platform origin and access platform credentials.

## Payment safety

Real blockchain payments are intentionally disabled. `CFS_PAYMENTS_MODE` may be `MOCK` or `TEST`; production blockchain mode fails closed until a real on-chain verifier is implemented and audited. MOCK/TEST UI must remain clearly identified as simulation and must not instruct users to send real funds.

## Local development

```bash
pip install -r backend/requirements.txt
export CFS_OWNER_BOOTSTRAP_TOKEN='replace-with-a-long-random-value'
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Development defaults to SQLite/local storage. Production requires persistent PostgreSQL and S3-compatible storage configuration.

## QA

The GitHub Actions workflow runs the full Python suite, the same suite against PostgreSQL, frontend JavaScript validation and Wrangler validation. Pushes to `main` also wait for the exact Render commit to become healthy, verify Cloudflare → Render readiness, and run a disposable production E2E flow covering registration, creator activation, game creation/editing, real upload/scan/storage, publication, catalog/play, saves, logout/login persistence and cleanup.

Useful local checks:

```bash
pytest -q
node --check frontend/app.js
node --check frontend/creator.js
node --check frontend/billing.js
python -m py_compile scripts/production_e2e.py
```

Production endpoints:

- Backend: `https://crypto-factory-studios.onrender.com`
- Frontend/edge: `https://crypto-factory-studios.cesargp9712.workers.dev`

See the `docs/` directory for payment architecture, security and validation notes.