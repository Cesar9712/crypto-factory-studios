import { EventBus } from '../core/EventBus.js';
import { StateStore } from '../core/StateStore.js';
import { PersistenceAdapter } from '../core/PersistenceAdapter.js';
import { createCombatMachine } from '../domain/combat/createCombatMachine.js';

const bus = new EventBus();
const persistence = new PersistenceAdapter({ key: 'cryptoquest:architecture:v1', schemaVersion: 1 });
const store = new StateStore({ player: null, ui: { screen: 'boot' }, meta: { bootedAt: Date.now() } }, bus);
const combat = createCombatMachine(bus);

const architecture = Object.freeze({
  version: '1.0.0-migration',
  bus,
  store,
  persistence,
  machines: Object.freeze({ combat }),
});

Object.defineProperty(window, 'CQArchitecture', {
  configurable: false,
  enumerable: false,
  writable: false,
  value: architecture,
});

function syncLegacyShell() {
  const shell = document.getElementById('game');
  if (!shell) return;
  const activeClass = [...shell.classList].find(name => name.endsWith('-active')) ?? 'unknown-active';
  const screen = activeClass.replace(/-active$/, '');
  if (store.select(state => state.ui.screen) !== screen) {
    store.update(state => { state.ui.screen = screen; }, { source: 'legacy-shell-adapter' });
    bus.emit('navigation:changed', { screen, source: 'legacy-shell-adapter' });
  }
}

let scheduled = false;
const scheduleSync = () => {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    syncLegacyShell();
  });
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', scheduleSync, { once: true });
} else {
  scheduleSync();
}

const observer = new MutationObserver(scheduleSync);
observer.observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });

bus.emit('architecture:ready', { version: architecture.version });
