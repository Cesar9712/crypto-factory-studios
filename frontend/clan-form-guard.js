const drafts={create:{name:'',tag:''},settings:{description:'',isOpen:null}};
let lastFocus=null;

function fieldKey(el){
  const form=el?.closest?.('#clan-create-form,#clan-settings-form');
  if(!form||!el?.name)return null;
  return {form:form.id==='clan-create-form'?'create':'settings',name:el.name};
}

function remember(el){
  const key=fieldKey(el);if(!key)return;
  if(el.type==='checkbox')drafts[key.form][key.name]=Boolean(el.checked);
  else drafts[key.form][key.name]=el.value;
  lastFocus={...key,start:typeof el.selectionStart==='number'?el.selectionStart:null,end:typeof el.selectionEnd==='number'?el.selectionEnd:null};
}

function restoreForm(formId,kind){
  const form=document.getElementById(formId);if(!form)return;
  Object.entries(drafts[kind]).forEach(([name,value])=>{
    const el=form.elements.namedItem(name);if(!el)return;
    if(el.type==='checkbox'){
      if(value!==null)el.checked=Boolean(value);
    }else if(typeof value==='string'&&value.length){
      el.value=value;
    }
  });
  if(lastFocus?.form===kind){
    const el=form.elements.namedItem(lastFocus.name);
    if(el&&document.activeElement!==el){
      requestAnimationFrame(()=>{
        if(!document.contains(el))return;
        try{el.focus({preventScroll:true});}catch{el.focus();}
        if(typeof el.setSelectionRange==='function'&&lastFocus.start!==null){
          const end=Math.min(el.value.length,lastFocus.end??lastFocus.start);
          const start=Math.min(el.value.length,lastFocus.start);
          try{el.setSelectionRange(start,end);}catch{}
        }
      });
    }
  }
}

function restore(){
  restoreForm('clan-create-form','create');
  restoreForm('clan-settings-form','settings');
}

document.addEventListener('input',e=>remember(e.target),true);
document.addEventListener('change',e=>remember(e.target),true);
document.addEventListener('focusin',e=>{const key=fieldKey(e.target);if(key)remember(e.target)},true);

document.addEventListener('submit',e=>{
  if(e.target?.id==='clan-create-form'){
    const f=new FormData(e.target);drafts.create.name=String(f.get('name')||'');drafts.create.tag=String(f.get('tag')||'');
  }
  if(e.target?.id==='clan-settings-form'){
    const f=new FormData(e.target);drafts.settings.description=String(f.get('description')||'');drafts.settings.isOpen=Boolean(f.get('isOpen'));
  }
},true);

window.addEventListener('nexus:clan',e=>{
  if(e.detail?.clan){drafts.create={name:'',tag:''};}
  lastFocus=null;
});

new MutationObserver(()=>restore()).observe(document.body,{childList:true,subtree:true});
setTimeout(restore,250);
