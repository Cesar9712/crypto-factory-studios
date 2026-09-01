(()=>{"use strict";
const VERSION="18.2.4";
let scheduled=false;

function wrapLeadingIcon(el){
  if(!el || el.querySelector(":scope > i")) return;
  const node=[...el.childNodes].find(n=>n.nodeType===Node.TEXT_NODE && n.textContent.trim());
  if(!node) return;
  const value=node.textContent.trim();
  if(!value) return;
  const i=document.createElement("i");
  i.textContent=value;
  node.replaceWith(i);
}

function renameAssassin(root){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const nodes=[];
  while(walker.nextNode()) nodes.push(walker.currentNode);
  for(const n of nodes){
    if(!n.nodeValue) continue;
    const next=n.nodeValue.replace(/PÍCARO/g,"ASESINO").replace(/Pícaro/g,"Asesino").replace(/pícaro/g,"asesino");
    if(next!==n.nodeValue) n.nodeValue=next;
  }
}

function hideNecromancer(root){
  for(const card of root.querySelectorAll(".class-cards .class-card")){
    const label=(card.querySelector("h2")?.textContent||"").trim().toUpperCase();
    const id=(card.getAttribute("data-class")||"").toLowerCase();
    if(id==="necromancer" || label==="NIGROMANTE") card.remove();
  }
}

function patch(){
  scheduled=false;
  const root=document.getElementById("game")||document.body;
  document.documentElement.dataset.cqVisual=VERSION;
  if(!document.title.includes("18.2.4")) document.title=document.title.replace(/V18\.2\.1[^·|]*/i,"V18.2.4 LayoutFix") || "CryptoQuest RPG · V18.2.4 LayoutFix";

  root.querySelectorAll(".more-grid button,.service-grid button,.npc-strip button,.spec-service").forEach(wrapLeadingIcon);
  renameAssassin(root);
  hideNecromancer(root);
}

function schedule(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(patch);
}

const start=()=>{
  patch();
  const root=document.getElementById("game")||document.body;
  new MutationObserver(schedule).observe(root,{childList:true,subtree:true});
};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});else start();
})();