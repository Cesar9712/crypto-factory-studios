(()=>{
  const panel=document.getElementById('panel');
  if(!panel||panel.__nexusPhase1Lifecycle)return;
  let proto=panel,descriptor=null;
  while(proto&&!descriptor){descriptor=Object.getOwnPropertyDescriptor(proto,'innerHTML');proto=Object.getPrototypeOf(proto)}
  if(!descriptor?.get||!descriptor?.set)return;
  Object.defineProperty(panel,'__nexusPhase1Lifecycle',{value:true,configurable:false});
  Object.defineProperty(panel,'innerHTML',{
    configurable:true,
    enumerable:descriptor.enumerable,
    get(){return descriptor.get.call(panel)},
    set(value){
      descriptor.set.call(panel,value);
      document.dispatchEvent(new CustomEvent('nexus:panel-render'));
    }
  });
})();
