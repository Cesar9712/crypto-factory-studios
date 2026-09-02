CryptoQuest RPG — V31.1 God Mode Visual / Mainline V18.2 Runtime

Gameplay base:
- Uses the current mainline V18.2 runtime payload inherited from the branch base.
- Runtime payload remains unchanged in data/p00.txt … data/p11.txt.
- Save, energy, progression, inventory, equipment, skills, talents, combat, missions, Battle Pass, payments, persistence, backend and APIs are unchanged.

Presentation:
- v31-god-mode.css is the comprehensive dark-fantasy visual system.
- v31-god-mode-runtime.js adds presentation-only tagging, touch feedback, restrained panel entrances and twelve pointer-free atmosphere motes.
- VISUAL_SYSTEM_V31.md contains art direction, coherence rules, optional variants, motion guidance, budgets and 4K/8K source-art prompts.
- Source art may be authored at 4K/8K, but browser exports must follow the mobile budgets in the visual guide.

Validation targets:
- 360x800, 390x844 and 412x915.
- Android/iOS safe areas.
- Reduced-motion and forced-colors fallbacks.
- No horizontal overflow and minimum practical touch targets.

Entry point: /games/cryptoquest/
Compatibility route: /games/cryptoquest/game.html
