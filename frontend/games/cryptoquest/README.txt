CryptoQuest RPG — CFS Preview

Presentation: V28 ULTRA HUD layered over the packaged V18.1A runtime.
Targets: 360x800, 390x844, 412x915, plus safe-area support for Android/iOS.

Architecture:
- index.html reconstructs the packaged game from data/p00.txt ... data/p11.txt.
- v27-mobile-aaa.css provides the authoritative mobile layout foundation.
- v28-ultra-hud.css adds premium HUD styling, cinematic vitals, touch states, equipment/inventory presentation, rarity treatments and responsive hardening.
- v28-ultra-runtime.js adds non-persistent presentation enhancements: touch accessibility, rarity tagging, inventory rarity filters, panel entrance animation and overflow diagnostics.

Safety boundary:
- The V28 presentation layer does not write game state, currency, XP, energy, inventory ownership, equipment ownership, Battle Pass state, payment state, backend data or APIs.
- No backend, database, payment or treasury configuration is modified by this preview.

Performance:
- VFX use CSS gradients/transforms/opacity rather than heavy canvas or WebGL overlays.
- prefers-reduced-motion disables presentation animations.
- Controls target a minimum 44px touch area when compatible with the existing DOM.

Entry point: /games/cryptoquest/
