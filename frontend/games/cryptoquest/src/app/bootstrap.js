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
import { PlayerProgressService } from '../domain/player/PlayerProgressService.js';
import { LegacyRuntimeAdapter } from '../infrastructure/compatibility/LegacyRuntimeAdapter.js';
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
const player = new PlayerProgressService({ store, bus });
const renderer = new RenderCoordinator({ store, bus, scheduler });
const legacy = new LegacyRuntimeAdapter({ store, bus, scheduler });

const services = Object.freeze({ navigation, energy, inventory, quests, talents, worldMap, player });
const architecture = Object.freeze({
  version: '3.1.0-migration',
  bus,
  store,
  persistence,
  api,
  scheduler,
  renderer,
  compatibility: Object.freeze({ legacy }),
  services,
  machines: Object.freeze({ combat }),
});

Object.defineProperty(window, 'CQArchitecture', {
  configurable: false,
  enumerable: false,
  writable: false,
  value: architecture,
});

let persistScheduled = false;
bus.on('state:changed', () => {
  if (persistScheduled) return;
  persistScheduled = true;
  scheduler.debounce('architecture-persist', () => {
    persistScheduled = false;
    persistence.save(store.getState());
  }, 120);
});

legacy.start();

window.addEventListener('pagehide', () => persistence.save(store.getState()));
window.addEventListener('beforeunload', () => {
  legacy.dispose();
  renderer.dispose();
  scheduler.dispose();
}, { once: true });

bus.emit('architecture:ready', { version: architecture.version });
