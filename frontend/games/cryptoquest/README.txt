CryptoQuest RPG — CFS Preview

Presentation: V31 MODO DIOS layered over the packaged V18.1A runtime.
Targets: 360x800, 390x844, 412x915, plus safe-area support for Android/iOS.

Architecture:
- index.html reconstructs the packaged game from data/p00.txt ... data/p11.txt.
- v27-mobile-aaa.css provides the authoritative mobile layout foundation.
- v28-ultra-hud.css adds premium HUD styling and safe touch presentation.
- v29-master-reference.css defines the dense master-reference hierarchy.
- v30-forged-obsidian.css establishes the forged obsidian material language.
- v31-god-mode.css unifies every screen: loading, creation, HUD, campaign,
  world, combat, character, equipment, inventory, talents, missions, services,
  dungeons, endgame, modals, rewards, navigation, icon containers and VFX.
- v28-ultra-runtime.js retains non-persistent accessibility/filter enhancements.
- v31-god-mode-runtime.js adds presentation-only screen tagging, panel entrances,
  touch feedback and a lightweight atmospheric layer.
- VISUAL_SYSTEM_V31.md documents art direction, tokens, animation, optional
  variants, 4K/8K generation prompts, export rules and visual QA requirements.

Safety boundary:
- V31 does not write game state, currency, XP, energy, inventory ownership,
  equipment ownership, Battle Pass state, payment state, backend data or APIs.
- No mechanics, statistics, balance, progression, persistence, backend,
  database, payment or treasury configuration is modified.
- The current launch classes remain Warrior, Mage, Archer and Assassin.

Performance:
- VFX use CSS gradients, opacity and transforms instead of canvas/WebGL.
- The runtime injects only 12 pointer-free decorative motes.
- prefers-reduced-motion disables decorative animation.
- Controls preserve minimum 44px touch targets when compatible with the DOM.
- 4K/8K is a source-art specification; mobile runtime exports remain optimized.

Entry point: /games/cryptoquest/

