# Crypto Factory Studios V0.3 — Cloudflare deployment

## Goal

Deploy the public portal safely without coupling the entire platform to one provider.

Recommended split:

- **Portal frontend:** Cloudflare Pages / static assets from `frontend/`
- **Backend API:** separate Python runtime/host
- **Game builds:** separate object storage/CDN origin
- **Database:** private backend-only database
- **Third-party uploads:** quarantine + scanner pipeline, never direct public serving

## Cloudflare Pages settings

Repository: `Cesar9712/crypto-factory-studios`

Production branch: `main`

Root / build directory: repository root

Build command: leave empty for the current static frontend

Build output directory: `frontend`

The frontend must not load large Godot/Web builds on the Home page. Game payloads should be fetched only after the player selects **Play**.

## Existing Cloudflare project

For the existing `crypto-factory-studios` Cloudflare project, connect GitHub only after the current `main` branch passes CFS QA.

Before enabling automatic production deployments:

1. Verify the GitHub repository and branch are correct.
2. Set output directory to `frontend`.
3. Keep production crypto mode disabled.
4. Do not add private keys, seed phrases, database passwords or blockchain secrets to Cloudflare environment variables unless a future backend service explicitly requires a secret and is designed to consume it server-side.
5. Verify `/`, `/billing.html`, `/creator.html`, `/profile.html`, `/game.html` and `/404.html` load correctly.
6. Verify security headers from `frontend/_headers` are applied.
7. Test Android Chrome at narrow widths before promoting a deployment.

## API routing

The current frontend calls `/api/v1/...`. A static Pages deployment alone cannot provide the Python API.

Until the backend is deployed behind the same public origin, account, creator, billing and payment actions should be treated as **staging / not online**.

Production options include:

- reverse proxy `/api/*` from the portal origin to a dedicated Python backend;
- use a dedicated API hostname such as `api.<domain>` with explicit CORS and secure cookie design;
- later migrate selected endpoints to another compatible runtime only after tests.

Do **not** expose the database directly to the browser.

## Game content isolation

Creator-uploaded game content should not share the authenticated portal security context.

Target architecture:

- Portal: `www.<domain>`
- API: `api.<domain>` or same-origin reverse proxy
- Game content: `games.<domain>` or isolated per-game origins

Third-party JavaScript must never inherit portal/admin cookies or privileged tokens.

## Large files / Godot Web

Do not use Cloudflare dashboard direct static upload as a workaround for large `wasm`/`pck` files when it exceeds current product limits.

Use object storage/CDN or another appropriate game-asset host and keep versioned build manifests in the platform database/backend.

Do not split WASM binaries artificially merely to bypass an upload limit.

## Release gate

A deployment may be promoted only when:

- GitHub CFS QA is green;
- no secrets are present in public files;
- production crypto remains disabled unless separately approved and tested;
- portal routes load on mobile and desktop;
- backend-dependent UI clearly handles API-unavailable states;
- Crypto Factory Web has been validated separately before being marked fully playable.

## Rollback

Keep the last known-good `main` commit and Cloudflare deployment available for rollback. Never delete the previous stable deployment merely because a newer build exists.
