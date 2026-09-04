# Infrastructure decision — Web3 RPG

## Audit snapshot

The current Render branch is a runnable demo, not yet a production game backend. It serves the static frontend and Node API from one process, keeps world state in `backend/data/state.json`, uses one hard-coded demo player in the browser, has no real authentication, no live PostgreSQL connection, no WebSocket layer, and no real-money settlement.

Critical findings:

1. JSON persistence is ephemeral on free hosting and must not be used for accounts or progress.
2. `/api/reset` is unauthenticated and resets the shared demo world.
3. `playerId` is client-supplied; production must derive identity from a verified session.
4. Wallet linking currently stores an address only; production wallet linking must use nonce/signature verification.
5. Marketplace settlement is demo Gold only. This is desired for the current stage.
6. The browser does not calculate authoritative rewards; game actions are validated by the backend, which is a good base to preserve.
7. No production rate limiting, security headers, request tracing, RLS, backups, or analytics are wired yet.

## Provider decisions

- Frontend: Cloudflare Pages for the static/PWA client once API origin configuration is added. Until then, keep the combined Render deployment to avoid breaking the current demo URL.
- Backend/API/Game server: Render Node Web Service.
- Database: Supabase PostgreSQL.
- Authentication: Supabase Auth (email/password first; wallet optional later).
- Game assets: Cloudflare R2 for large public assets; Supabase Storage only for small auth-bound user files if needed.
- CDN/DNS: Cloudflare.
- WebSockets: Render WebSocket endpoint when real-time gameplay actually requires it. Do not add Redis/WebSockets before a feature needs them.
- Cache: process memory for immutable definitions initially; add Redis only after measured need.
- Analytics: Cloudflare Web Analytics initially; gameplay events stored server-side/Postgres, with a dedicated analytics product only when volume justifies it.
- Logs: Render service logs + Supabase logs; add centralized error tracking later.
- Smart-contract testing: local EVM (Anvil/Hardhat) first, then an EVM testnet such as Base Sepolia. No mainnet deployment in this phase.
- CI/CD: GitHub Actions for test/lint/build; Render auto-deploy for the deployment branch.
- Production domain: Cloudflare DNS with `game.<domain>` for frontend and `api.<domain>` for backend.
- Backups: Supabase Pro automatic backups when production starts; during free-stage development use explicit schema migrations and periodic external dumps before important changes.

## Scaling path

- Up to ~100 players: one Render API + Supabase Free/entry plan is sufficient for development/testing.
- ~1,000 players: paid Render instance, Supabase Pro, asset CDN/R2, measured connection pooling.
- ~10,000 players: split background jobs/workers, Redis/queue if measured contention exists, separate read-heavy services, stronger observability.
- ~100,000 players: multi-instance game API, partitioned workloads, dedicated queues/cache, database scaling/read replicas, load and chaos testing.

Do not pre-build the 100k architecture before load data justifies it.
