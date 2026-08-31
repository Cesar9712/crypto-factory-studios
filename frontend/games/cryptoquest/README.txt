CryptoQuest RPG — V21 Master Production

Runtime architecture:
- Stable monolithic V19 gameplay core: game.html
- V20 premium dark-fantasy and Battle Pass layer
- V21 master visual layer derived from the CryptoQuest AAA design system
- Cloudflare Worker edge injection with no-store game delivery
- Production mobile, core and smoke QA through GitHub Actions

Entry point: /games/cryptoquest/
Canonical game: /games/cryptoquest/game.html

V21 changes are visual/QA only. Gameplay, saves, battle economy, premium ownership,
payment verification and reward delivery continue to use the existing stable runtime.
