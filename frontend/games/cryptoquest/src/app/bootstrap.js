import { EventBus } from '../core/EventBus.js';
import { StateStore } from '../core/StateStore.js';
import { PersistenceAdapter } from '../core/PersistenceAdapter.js';
import { ApiClient } from '../core/ApiClient.js';
import { Scheduler } from '../core/Scheduler.js';
import { createCombatMachine } from '../domain/combat/createCombatMachine.js';
import { NavigationController } from '../domain/navigation/NavigationController.js';
import { EnergyService } from '../domain/energy/EnergyService.js';
import { InventoryService } from '../domain/inventory/InventoryService.js';
import { QuestService } from '../domain/quests/QuestService.js';
import { TalentTreeService } from '../domain/talents/TalentTreeService.js';
import { MapGraphService } from '../domain/map/MapGraphService.js';
import { RenderCoordinator } from '../ui/RenderCoordinator.js';

const bus = new EventBus();
const scheduler = new Scheduler();
const persistence = new PersistenceAdapter({ key: 'cryptoquest:architecture:v3', schemaVersion: 3 });
const api = new ApiClient({ baseUrl: '' });
const initialState = persistence.load({
  player: null,
  ui: { screen: 'boot', previousScreen: null },
  runtime: { legacyDetected: false },
  quests: { active: {}, completed: {}, trackedId: null },
  talents: { trees: {}, unlocked: {}, points: 0 },
  world: { graphs: {}, currentGraphId: null, currentNodeId: null, unlockedNodes: {} },
  meta: { bootedAt: Date.now(), architectureVersion: 3 },
});
const store = new StateStore(initialState, bus);
const combat = createCombatMachine(bus);
const navigation = new NavigationController({ store, bus });
const energy = new EnergyService({ store, bus });
const inventory = new InventoryService({ store, bus });
const quests = new QuestService({ store, bus });
const talents = new TalentTreeService({ store, bus });
const worldMap = new MapGraphService({ store, bus });
const renderer = new RenderCoordinator({ store, bus, scheduler });

const services = Object.freeze({ navigation, energy, inventory, quests, talents, worldMap });
const architecture = Object.freeze({
  version: '3.0.0-migration',
  bus,
  store,
  persistence,
  api,
  scheduler,
  renderer,
  services,
  machines: Object.freeze({ combat }),
});

Object.defineProperty(window, 'CQArchitecture', {
  configurable: false,
  enumerable: false,
  writable: false,
  value: architecture,
});

function legacyGame() {
  try { return window.CryptoQuestCore?.getGame?.() ?? window.game ?? null; } catch { return null; }
}

function normalizeLegacyPlayer(game) {
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

function syncLegacyState() {
  const shell = document.getElementById('game');
  const activeClass = shell ? [...shell.classList].find(name => name.endsWith('-active')) : null;
  const screen = activeClass ? activeClass.replace(/-active$/, '') : store.select(s => s.ui.screen);
  const game = legacyGame();
  const player = normalizeLegacyPlayer(game);
  const prevScreen = store.select(s => s.ui.screen);
  const prevLegacy = store.select(s => s.runtime?.legacyDetected);

  if (screen !== prevScreen || Boolean(game) !== prevLegacy || (player && !store.select(s => s.player))) {
    store.update(state => {
      state.ui ??= {};
      state.runtime ??= {};
      if (screen !== state.ui.screen) {
        state.ui.previousScreen = state.ui.screen ?? null;
        state.ui.screen = screen;
      }
      state.runtime.legacyDetected = Boolean(game);
      if (player && !state.player) state.player = player;
    }, { source: 'legacy-runtime-bridge' });
    if (screen !== prevScreen) bus.emit('navigation:changed', { screen, source: 'legacy-runtime-bridge' });
  }
}

let persistScheduled = false;
bus.on('state:changed', () => {
  if (persistScheduled) return;
  persistScheduled = true;
  scheduler.debounce('architecture-persist', () => {
    persistScheduled = false;
    persistence.save(store.getState());
  }, 120);
});

const scheduleSync = () => scheduler.frame('legacy-sync', syncLegacyState);
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scheduleSync, { once: true });
else scheduleSync();
window.addEventListener('load', scheduleSync, { once: true });

const observer = new MutationObserver(scheduleSync);
observer.observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });

window.addEventListener('pagehide', () => persistence.save(store.getState()));
window.addEventListener('beforeunload', () => {
  observer.disconnect();
  renderer.dispose();
  scheduler.dispose();
}, { once: true });

bus.emit('architecture:ready', { version: architecture.version });
