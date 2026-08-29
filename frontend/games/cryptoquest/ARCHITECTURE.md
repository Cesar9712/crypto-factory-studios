# CryptoQuest RPG — Canonical Architecture V5

CryptoQuest uses a modular browser-game architecture with explicit boundaries. New gameplay code must be added to the canonical folders below. `src/` is compatibility-only and must not contain implementations.

## Canonical layout

```text
frontend/games/cryptoquest/
├── core/       # composition root, events, state, FSM, API, persistence, scheduling, loader
├── systems/    # combat, energy, inventory, equipment, economy, quests
├── player/     # progression, skills, talents and player-owned state behavior
├── world/      # map graph and world-domain behavior
├── levels/     # level registry and future level data modules
├── ui/         # render coordination, navigation and screen-level UI controllers
├── graphics/   # boot/runtime CSS, shaders, textures, materials and VFX boundary
├── audio/      # music, SFX and voice boundary
├── scripts/    # scripted events and legacy runtime compatibility boundary
├── config/     # game/runtime configuration
├── assets/     # stable asset catalog boundary
├── build/      # runtime generation, compression/export/deployment preparation
├── net/        # future network/client synchronization boundary
└── src/        # temporary backwards-compatible re-export adapters only
```

## Runtime ownership

`core/bootstrap.js` is the composition root. It constructs the EventBus, StateStore, Scheduler, persistence, API client, combat FSM and domain services, then exposes the frozen `window.CQArchitecture` integration boundary.

`core/loader.js` is the only entry loader used by `index.html`. It prefers the generated `runtime.html`. A packed-source fallback exists only while the generated runtime migration is being validated; it must be removed once production has passed with generated runtime artifacts.

## Historical runtime extraction

The historical HTML source is still archived as gzip/base64 chunks under `data/p00.txt` through `data/p11.txt`. These chunks are build inputs, not the target production architecture.

`.github/workflows/cryptoquest-unpack.yml` decodes the archive to a temporary `game.source.html`, runs `build/normalize-runtime.mjs`, and generates:

- `runtime.html`
- `graphics/runtime/legacy-XX.css`
- `scripts/runtime/legacy-XX.js`
- `build/runtime-manifest.json`

The normalizer applies the currently required compatibility corrections before externalizing executable inline scripts and style blocks. The temporary decoded source is never committed.

## Compatibility policy

Files under `src/core`, `src/domain`, `src/ui`, `src/infrastructure` and `src/app` are adapters only. They exist so old imports keep working while the canonical paths become authoritative. They must contain imports/re-exports, not game implementations.

`LegacyRuntimeAdapter` is isolated under `scripts/compatibility`. It is the only architecture module allowed to read legacy global game state and translate it into canonical state. New systems must not access legacy globals directly.

## Dependency rules

- `core` has no gameplay dependency.
- `systems` may depend on `core`, never on DOM/UI implementations.
- `player` may depend on core contracts/state, not screen markup.
- `world` may depend on core contracts/state, not UI.
- `ui` consumes state/services/events; gameplay rules belong in systems/player/world.
- `graphics` and `audio` react to UI/events; they do not own gameplay state.
- `net` must communicate through explicit service interfaces and events.
- Cross-module communication should use injected services, StateStore or EventBus rather than new globals.

## Persistence

The architecture shadow store uses the stable `cryptoquest:architecture:v5` key. The historical gameplay save remains untouched during migration so existing player progression is preserved. Changes to persistence require explicit schema handling and regression tests for reload/backup recovery.

## Mobile and QA contract

Critical mobile viewports are 360×800, 390×844 and 412×915. Required automated checks cover startup, character creation, navigation, talent selection/persistence, campaign energy consumption, secondary screens, combat entry, horizontal overflow and JavaScript errors.

## Future extension

Advanced AI belongs behind `systems` interfaces. Multiplayer/server synchronization belongs under `net`. Web3/payment integrations remain backend/API responsibilities and must not be embedded in UI. 4K/8K source assets can live under graphics/assets, while mobile builds should use compressed variants selected at build/runtime configuration boundaries.
