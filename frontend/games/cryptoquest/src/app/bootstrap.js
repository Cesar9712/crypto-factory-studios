import { EventBus, StateStore, PersistenceAdapter, ApiClient, Scheduler } from '../../core/index.js';
import { createCombatMachine, EnergyService, InventoryService, EquipmentService, EconomyService, QuestService } from '../../systems/index.js';
import { PlayerProgressService, SkillService, TalentTreeService } from '../../player/index.js';
import { MapGraphService } from '../../world/index.js';
import { NavigationController, RenderCoordinator } from '../../ui/index.js';
import { LegacyRuntimeAdapter } from '../../scripts/index.js';
import { LevelRegistry } from '../../levels/LevelRegistry.js';
import { GAME_CONFIG } from '../../config/game.config.js';

const bus=new EventBus();
const scheduler=new Scheduler();
const persistence=new PersistenceAdapter(GAME_CONFIG.persistence);
const api=new ApiClient({baseUrl:''});
const initialState=persistence.load({
 player:null,
 ui:{screen:'boot',previousScreen:null},
 runtime:{legacyDetected:false},
 quests:{active:{},completed:{},trackedId:null},
 talents:{trees:{},unlocked:{},points:0},
 skills:{definitions:{},unlocked:{},levels:{},cooldowns:{}},
 world:{graphs:{},currentGraphId:null,currentNodeId:null,unlockedNodes:{}},
 meta:{bootedAt:Date.now(),architectureVersion:GAME_CONFIG.architectureVersion}
});
const store=new StateStore(initialState,bus);
const combat=createCombatMachine(bus);
const navigation=new NavigationController({store,bus});
const energy=new EnergyService({store,bus});
const inventory=new InventoryService({store,bus});
const equipment=new EquipmentService({store,bus});
const economy=new EconomyService({store,bus});
const skills=new SkillService({store,bus});
const quests=new QuestService({store,bus});
const talents=new TalentTreeService({store,bus});
const worldMap=new MapGraphService({store,bus});
const player=new PlayerProgressService({store,bus});
const levels=new LevelRegistry();
const renderer=new RenderCoordinator({store,bus,scheduler});
const legacy=new LegacyRuntimeAdapter({store,bus,scheduler});
const services=Object.freeze({navigation,energy,inventory,equipment,economy,skills,quests,talents,worldMap,player});
const architecture=Object.freeze({version:'4.0.0-migration',layoutVersion:GAME_CONFIG.architectureVersion,bus,store,persistence,api,scheduler,renderer,levels,compatibility:Object.freeze({legacy}),services,machines:Object.freeze({combat})});
Object.defineProperty(window,'CQArchitecture',{configurable:false,enumerable:false,writable:false,value:architecture});
let persistScheduled=false;
bus.on('state:changed',()=>{if(persistScheduled)return;persistScheduled=true;scheduler.debounce('architecture-persist',()=>{persistScheduled=false;persistence.save(store.getState());},GAME_CONFIG.persistence.debounceMs);});
legacy.start();
window.addEventListener('pagehide',()=>persistence.save(store.getState()));
window.addEventListener('beforeunload',()=>{legacy.dispose();renderer.dispose();scheduler.dispose();},{once:true});
bus.emit('architecture:ready',{version:architecture.version,layoutVersion:architecture.layoutVersion});
