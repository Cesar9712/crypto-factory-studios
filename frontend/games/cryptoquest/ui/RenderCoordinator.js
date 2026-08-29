export class RenderCoordinator {
  constructor({ store, bus, scheduler }) { this.store=store;this.bus=bus;this.scheduler=scheduler;this.renderers=new Map();this.unsubscribe=bus?.on('state:changed',()=>this.requestRender())??null; }
  register(name,renderer) { if(!name||typeof renderer!=='function')throw new TypeError('Renderer requires name and function');this.renderers.set(name,renderer);this.requestRender(name);return()=>this.renderers.delete(name); }
  requestRender(name=null) { this.scheduler.frame(`render:${name??'all'}`,()=>{const state=this.store.getState();if(name){this.renderers.get(name)?.(state);return;}for(const renderer of this.renderers.values())renderer(state);this.bus?.emit('ui:rendered',{count:this.renderers.size,at:globalThis.performance?.now?.()??Date.now()});}); }
  dispose(){this.unsubscribe?.();this.renderers.clear();}
}
