# CryptoQuest RPG — Modular Architecture

This document defines the canonical module boundaries for the game. During migration, the historical packed runtime remains behind the compatibility adapter so saved games and existing gameplay are not broken.

## Canonical layout

- `core/` — shared runtime primitives: events, state, persistence, scheduling, API boundary and state machines.
- `systems/` — gameplay systems: combat, energy, inventory, equipment, economy and quests.
- `player/` — player progression, skills and talent tree.
- `world/` — world graph and travel/map state.
- `levels/` — independent level definitions and registry. Future level data should live in JSON/modules here rather than in UI code.
- `ui/` — navigation and render coordination. Screen-specific renderers should be added here.
- `graphics/` — shaders, visual effects, materials and render assets only; no gameplay rules.
- `audio/` — music, SFX and voice definitions only; no gameplay rules.
- `scripts/` — scripted events, cinematics and the isolated legacy compatibility boundary.
- `config/` — runtime, controls, graphics, audio and locale configuration.
- `assets/` — source game assets grouped by type.
- `build/` — build/export/compression tooling and manifests.
- `net/` — HTTP/network boundary and future synchronization clients.

## Runtime composition

`src/app/bootstrap.js` is the composition root. It imports only canonical module boundaries, creates the event bus/store/services, exposes the read-only `window.CQArchitecture` integration handle, starts compatibility synchronization, and owns shutdown/persistence lifecycle.

## Dependency rules

1. UI may call systems/player/world services, but gameplay services must not import UI.
2. Systems communicate through the central EventBus and StateStore rather than direct DOM access.
3. Network access goes through `ApiClient`/`net` only.
4. Legacy globals and DOM inspection are restricted to `LegacyRuntimeAdapter` while migration is active.
5. Level, item, skill and talent definitions should be data-first and externalized from render code.
6. Save schema changes require migration and must never silently discard player progression.

## Existing modules

- Combat: finite-state machine (`idle -> playerTurn -> resolving -> enemyTurn -> finished`).
- Energy: spend/restore/snapshot service.
- Inventory and equipment: item/equipment state services.
- Economy: currency credit/debit boundary.
- Skills: unlock, levels and cooldowns.
- Talents: tree definitions/unlocks/points.
- Quests: active/completed/tracked state.
- World: graph-based nodes/routes.
- Player: level/XP/progression.
- Persistence: versioned local storage envelope plus legacy save compatibility.
- Rendering: requestAnimationFrame-coordinated render scheduling.

## Migration policy

The packed historical runtime is not removed until each behavior it owns has an equivalent canonical module and regression coverage. Old paths under `src/domain` currently remain compatibility implementation details; canonical imports are now routed through the top-level module boundaries. Once each system is fully extracted, the compatibility path can be deleted without changing public imports.

## Future expansion

- 4K/8K assets: add through `graphics/` and `assets/` with mobile variants and lazy loading.
- Advanced AI: create `systems/ai/` behind events/state, never inside UI renderers.
- Multiplayer: extend `net/` with protocol/session/sync modules and authoritative server validation.
- Web3: keep wallet/payment ownership outside deterministic gameplay services; expose only validated application commands.
- Mobile export/PWA: build profiles belong in `build/`, with responsive UI retained in `ui/`.
