# Crypto Factory Studios V0.3 — Creator Platform + Crypto Payment Foundation

A security-first Web game publishing platform for players and creators. V0.3 preserves the V0.1 upload/quarantine/publishing foundation and adds a redesigned Creator Billing experience plus a server-authoritative crypto-payment foundation.

## What works
- Player accounts and Creator activation.
- `PLATFORM_OWNER` with `internal_unlimited` and `billing_exempt`.
- FREE / PLUS / PRO creator plans server-side.
- Creator game drafts, secure ZIP upload, quarantine, scan gate and publication.
- Per-game cloud-save model.
- Admin moderation and audit log.
- Browser auth upgraded to HttpOnly SameSite=Strict session cookies plus CSRF protection.
- Creator Billing page.
- Server-side product catalog and prices.
- Payment methods: TRON USDT, BNB Smart Chain BSC-USD route, native SOL.
- Quotes, orders, idempotency, anti-replay, mock verification, entitlements and purchase history.
- Admin payment ledger.

## Payment safety
`CFS_PAYMENTS_MODE=MOCK` is the default. V0.3 deliberately refuses PRODUCTION payment mode. No private keys, seed phrases or wallet passwords are stored or requested.

## Run locally
```bash
cd CryptoFactoryStudios_V0.3
pip install -r backend/requirements.txt
export CFS_OWNER_BOOTSTRAP_TOKEN='replace-with-a-long-random-value'
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/billing.html`.

## QA
Run:
```bash
pytest -q
node --check frontend/app.js
node --check frontend/creator.js
node --check frontend/billing.js
```

See `docs/PAYMENT_ARCHITECTURE.md`, `docs/PAYMENT_SECURITY.md`, `docs/PAYMENT_QA.md`, and `docs/VALIDATION_V02.md`.