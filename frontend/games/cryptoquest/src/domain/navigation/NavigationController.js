const VALID_SCREENS = new Set(['home','adventure','hero','bag','talents','more','combat','bastion','dungeons','expeditions','shop']);

export class NavigationController {
  constructor({ store, bus }) {
    this.store = store;
    this.bus = bus;
  }

  current() { return this.store.select(s => s.ui?.screen || 'boot'); }

  go(screen, meta = {}) {
    if (!VALID_SCREENS.has(screen)) throw new Error(`Unknown screen: ${screen}`);
    if (screen === this.current()) return false;
    this.store.update(state => {
      state.ui ??= {};
      state.ui.previousScreen = state.ui.screen ?? null;
      state.ui.screen = screen;
    }, { source: 'navigation-controller', ...meta });
    this.bus.emit('navigation:requested', { screen, ...meta });
    return true;
  }
}
