export class LegacyRuntimeAdapter {
  constructor({ store, bus, scheduler, documentRef = document, windowRef = window }) {
    this.store = store;
    this.bus = bus;
    this.scheduler = scheduler;
    this.document = documentRef;
    this.window = windowRef;
    this.observer = null;
  }

  legacyGame() {
    try { return this.window.CryptoQuestCore?.getGame?.() ?? this.window.game ?? null; } catch { return null; }
  }

  normalizePlayer(game) {
    const p = game?.player ?? game?.character ?? null;
    if (!p) return null;
    const currentEnergy = Number(p.energy?.current ?? p.energy ?? game?.energy ?? 0);
    const maxEnergy = Number(p.energy?.max ?? p.maxEnergy ?? game?.maxEnergy ?? currentEnergy);
    return {
      id: p.id ?? null,
      name: p.name ?? p.username ?? '',
      classId: p.classId ?? p.class ?? null,
      level: Number(p.level ?? 1),
      xp: Number(p.xp ?? p.exp ?? 0),
      currencies: {
        gold: Number(p.gold ?? game?.gold ?? 0),
        premium: Number(p.premium ?? p.gems ?? game?.premium ?? 0),
      },
      energy: { current: currentEnergy, max: maxEnergy, updatedAt: Date.now() },
      inventory: {
        items: structuredClone(p.inventory?.items ?? game?.inventory ?? []),
        equipped: structuredClone(p.inventory?.equipped ?? p.equipment ?? game?.equipment ?? {}),
      },
    };
  }

  currentScreen() {
    const shell = this.document.getElementById('game');
    const activeClass = shell ? [...shell.classList].find(name => name.endsWith('-active')) : null;
    return activeClass?.replace(/-active$/, '') ?? null;
  }

  sync() {
    const game = this.legacyGame();
    const player = this.normalizePlayer(game);
    const screen = this.currentScreen() ?? this.store.select(state => state.ui?.screen ?? 'boot');
    const previousScreen = this.store.select(state => state.ui?.screen);
    const legacyDetected = Boolean(game);
    const previousLegacy = Boolean(this.store.select(state => state.runtime?.legacyDetected));
    const hasPlayer = Boolean(this.store.select(state => state.player));

    if (screen === previousScreen && legacyDetected === previousLegacy && (!player || hasPlayer)) return;

    this.store.update(state => {
      state.ui ??= {};
      state.runtime ??= {};
      if (screen !== state.ui.screen) {
        state.ui.previousScreen = state.ui.screen ?? null;
        state.ui.screen = screen;
      }
      state.runtime.legacyDetected = legacyDetected;
      if (player && !state.player) state.player = player;
    }, { source: 'legacy-runtime-adapter' });

    if (screen !== previousScreen) this.bus?.emit('navigation:changed', { screen, source: 'legacy-runtime-adapter' });
  }

  scheduleSync = () => this.scheduler.frame('legacy-sync', () => this.sync());

  start() {
    if (this.observer) return;
    if (this.document.readyState === 'loading') this.document.addEventListener('DOMContentLoaded', this.scheduleSync, { once: true });
    else this.scheduleSync();
    this.window.addEventListener('load', this.scheduleSync, { once: true });
    this.observer = new MutationObserver(this.scheduleSync);
    this.observer.observe(this.document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });
  }

  dispose() {
    this.observer?.disconnect();
    this.observer = null;
  }
}
