async function loadGeneratedRuntime() {
  const response = await fetch('/games/cryptoquest/runtime.html', { cache: 'no-store' });
  if (!response.ok) return null;
  const html = await response.text();
  if (!html.includes('V5-CANONICAL') || !html.includes('core/bootstrap.js?v=5.0.0')) return null;
  return html;
}

async function loadPackedFallback() {
  const names = Array.from({ length: 12 }, (_, i) => `data/p${String(i).padStart(2, '0')}.txt`);
  const parts = await Promise.all(names.map(async name => {
    const response = await fetch(name, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${name}: ${response.status}`);
    return response.text();
  }));
  const encoded = parts.join('');
  const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  let html = await new Response(stream).text();

  const itemCountLine = "const ITEM_DEFINITION_COUNT=ITEM_VARIANTS.length+Object.keys(UNIQUE_ITEMS).length+Object.keys(MYTHIC_ITEMS).length;";
  const mythicFinalize = "for(const item of [...Object.values(UNIQUE_ITEMS),...Object.values(MYTHIC_ITEMS)]){";
  const talentSpecGuard = "(node.specialization&&node.specialization!==p.specialization)";
  const talentBranchGuard = "!p.specialization||branch.specialization!==p.specialization?'foreign':''";
  const talentAvailableGuard = "node.specialization===p.specialization";
  const talentMigrationGuard = "!requestedTalents.includes(node.id)||node.specialization!==p.specialization||node.requires&&!acceptedTalents.includes(node.requires)||node.choiceGroup&&choiceGroups.has(node.choiceGroup)";
  const campaignEnergyMarker = "}let enemy=createEncounter(base.id,{difficulty:game.difficulty,forceElite});";
  if (!html.includes('...SPECIALIZATION_SETS') || !/^const SPECIALIZATION_SETS=.*;$/m.test(html) || !html.includes(itemCountLine) || !html.includes(mythicFinalize) || !html.includes(talentSpecGuard) || !html.includes(talentBranchGuard) || !html.includes(talentAvailableGuard) || !html.includes(talentMigrationGuard) || !html.includes(campaignEnergyMarker)) {
    throw new Error('CryptoQuest fallback: faltan marcadores de gameplay esperados');
  }
  html = html.replace(/\s*\.\.\.SPECIALIZATION_SETS\s*\n};/, '\n};');
  html = html.replace(/^(const SPECIALIZATION_SETS=.*;)$/m, '$1\nObject.assign(SETS,SPECIALIZATION_SETS);');
  html = html.replace(itemCountLine, 'let ITEM_DEFINITION_COUNT=ITEM_VARIANTS.length;');
  html = html.replace(mythicFinalize, 'ITEM_DEFINITION_COUNT=ITEM_VARIANTS.length+Object.keys(UNIQUE_ITEMS).length+Object.keys(MYTHIC_ITEMS).length;\n' + mythicFinalize);
  html = html.replaceAll(talentSpecGuard, '(p.specialization&&node.specialization&&node.specialization!==p.specialization)');
  html = html.replaceAll(talentBranchGuard, "p.specialization&&branch.specialization!==p.specialization?'foreign':''");
  html = html.replaceAll(talentAvailableGuard, '(!p.specialization||node.specialization===p.specialization)');
  html = html.replace(talentMigrationGuard, "!requestedTalents.includes(node.id)||(p.specialization&&node.specialization!==p.specialization)||node.requires&&!acceptedTalents.includes(node.requires)||node.choiceGroup&&choiceGroups.has(node.choiceGroup)");
  html = html.replace(campaignEnergyMarker, "}if(!spendEnergy(game,1)){toast('Energía insuficiente');return;}let enemy=createEncounter(base.id,{difficulty:game.difficulty,forceElite});");
  html = html.replaceAll('+${e.xp} EXP · +${e.gold} ORO</em>', '+${e.xp} EXP · +${e.gold} ORO · ⚡ 1</em>');
  html = html.replaceAll('+${e.xp} EXP · +${e.gold} 🪙</em>', '+${e.xp} EXP · +${e.gold} 🪙 · ⚡ 1</em>');

  const presentation = '<link rel="stylesheet" href="/games/cryptoquest/v27-mobile-aaa.css?v=27.0.0"><link rel="stylesheet" href="/games/cryptoquest/v28-ultra-hud.css?v=28.0.0"><link rel="stylesheet" href="/games/cryptoquest/v29-master-reference.css?v=29.0.0"><link rel="stylesheet" href="/games/cryptoquest/v30-forged-obsidian.css?v=30.0.0"><link rel="stylesheet" href="/games/cryptoquest/v32-gameplay-fixes.css?v=32.0.1"><meta name="cryptoquest-architecture" content="V5-CANONICAL"><meta name="cryptoquest-gameplay" content="V32-TALENT-ENERGY-HOME">';
  const runtime = '<script src="/games/cryptoquest/v28-ultra-runtime.js?v=28.0.0" defer><\/script><script src="/games/cryptoquest/v31-bootguard.js?v=31.0.0" defer><\/script><script type="module" src="/games/cryptoquest/core/bootstrap.js?v=5.0.0"><\/script>';
  html = html.includes('</head>') ? html.replace('</head>', presentation + '</head>') : presentation + html;
  const bodyEnd = html.lastIndexOf('</body>');
  return bodyEnd >= 0 ? html.slice(0, bodyEnd) + runtime + html.slice(bodyEnd) : html + runtime;
}

(async () => {
  try {
    const html = await loadGeneratedRuntime() ?? await loadPackedFallback();
    document.open();
    document.write(html);
    document.close();
  } catch (error) {
    const element = document.getElementById('err');
    if (element) element.textContent = `No se pudo cargar CryptoQuest: ${error.message}`;
    console.error(error);
  }
})();
