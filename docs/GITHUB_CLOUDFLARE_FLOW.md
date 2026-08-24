# GitHub → Cloudflare deployment flow

## Source of truth
`main` is the deployable source branch for the portal frontend. Keep real secrets out of the repository.

## Cloudflare target
Use the existing `crypto-factory-studios` Worker and connect it to this GitHub repository with Workers Builds. The static asset directory is `frontend/`, configured in `wrangler.toml`.

## Deployment rule
- Push to `main` only after QA passes.
- Cloudflare builds/deploys from GitHub.
- Keep the Python backend separate from the static Worker deployment.
- Do not deploy `.env`, SQLite runtime databases, quarantine uploads, or creator build archives as static assets.

## Rollback
Cloudflare Workers versions/deployments can be used to roll back the frontend. Git history remains the code rollback source.

## Current payments safety
Production crypto payments must stay disabled until backend hosting, blockchain verification, payment reconciliation, rate limiting, HTTPS, and controlled real-network QA are complete.
