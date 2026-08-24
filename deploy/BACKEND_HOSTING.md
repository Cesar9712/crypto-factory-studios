# Crypto Factory Studios — Backend Hosting

## Purpose

The Cloudflare Worker serves the public portal and proxies `/api/*` to a separate HTTPS Python backend through the `API_ORIGIN` Worker variable.

The backend is a FastAPI application (`backend.app.main:app`) packaged with `backend/Dockerfile`.

## Required production characteristics

Use a host that supports:

- Docker or Python 3.13.
- HTTPS.
- Persistent database/storage appropriate for the selected database mode.
- Environment variables/secrets stored outside Git.
- A configurable `PORT` environment variable.
- Health checks against `/health` and readiness checks against `/ready` where supported.

Do not put database passwords, session secrets, bootstrap tokens, blockchain provider secrets, private keys, seed phrases, or wallet passwords in GitHub.

## Container launch

Build from repository root:

```bash
docker build -f backend/Dockerfile -t crypto-factory-studios-api .
```

Run locally:

```bash
docker run --rm -p 8000:8000 \
  -e PORT=8000 \
  -e CFS_ENV=production \
  -e CFS_PAYMENTS_MODE=MOCK \
  -e CFS_OWNER_BOOTSTRAP_TOKEN='replace-with-a-long-random-secret' \
  crypto-factory-studios-api
```

Then validate:

```text
GET /health
GET /ready
```

## Cloudflare connection

After the backend has a stable HTTPS origin, configure the Worker variable:

```text
API_ORIGIN=https://your-api-host.example
```

Do not include a trailing slash.

The Worker then forwards requests such as:

```text
https://portal.example/api/v1/games
```

to:

```text
https://your-api-host.example/api/v1/games
```

## Security gate

Before enabling real users:

1. Keep `CFS_PAYMENTS_MODE=MOCK`.
2. Use strong secrets through the hosting provider secret store.
3. Confirm `/health` and `/ready` return expected status codes.
4. Confirm authentication cookies remain Secure/HttpOnly in production.
5. Configure explicit allowed origins; do not use wildcard CORS in production.
6. Confirm upload quarantine and malware scanning are available before public creator uploads.
7. Run GitHub QA and a controlled staging smoke test.
8. Back up persistent data before upgrades.

## Rollback

Cloudflare can roll the portal/edge Worker back independently. The backend host should also retain at least the previous known-good container/image or deploy revision. Avoid schema changes that cannot be rolled back without a documented migration/restore path.
