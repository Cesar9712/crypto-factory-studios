import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const root = resolve('frontend/games/cryptoquest');
const sourcePath = resolve(root, 'game.source.html');
const runtimePath = resolve(root, 'runtime.html');
const stylesDir = resolve(root, 'graphics/runtime');
const scriptsDir = resolve(root, 'scripts/runtime');

let html = await readFile(sourcePath, 'utf8');

function requiredReplace(search, replacement, label) {
  if (!html.includes(search)) throw new Error(`Missing required runtime marker: ${label}`);
  html = html.replace(search, replacement);
}

const itemCountLine = "const ITEM_DEFINITION_COUNT=ITEM_VARIANTS.length+Object.keys(UNIQUE_ITEMS).length+Object.keys(MYTHIC_ITEMS).length;";
const mythicFinalize = "for(const item of [...Object.values(UNIQUE_ITEMS),...Object.values(MYTHIC_ITEMS)]){";
const talentSpecGuard = "(node.specialization&&node.specialization!==p.specialization)";
const talentBranchGuard = "!p.specialization||branch.specialization!==p.specialization?'foreign':''";
const talentAvailableGuard = "node.specialization===p.specialization";
const talentMigrationGuard = "!requestedTalents.includes(node.id)||node.specialization!==p.specialization||node.requires&&!acceptedTalents.includes(node.requires)||node.choiceGroup&&choiceGroups.has(node.choiceGroup)";
const campaignEnergyMarker = "}let enemy=createEncounter(base.id,{difficulty:game.difficulty,forceElite});";

if (!html.includes('...SPECIALIZATION_SETS')) throw new Error('Missing SPECIALIZATION_SETS spread marker');
html = html.replace(/\s*\.\.\.SPECIALIZATION_SETS\s*\n};/, '\n};');
if (!/^const SPECIALIZATION_SETS=.*;$/m.test(html)) throw new Error('Missing SPECIALIZATION_SETS definition');
html = html.replace(/^(const SPECIALIZATION_SETS=.*;)$/m, '$1\nObject.assign(SETS,SPECIALIZATION_SETS);');
requiredReplace(itemCountLine, 'let ITEM_DEFINITION_COUNT=ITEM_VARIANTS.length;', 'item count initialization');
requiredReplace(mythicFinalize, 'ITEM_DEFINITION_COUNT=ITEM_VARIANTS.length+Object.keys(UNIQUE_ITEMS).length+Object.keys(MYTHIC_ITEMS).length;\n' + mythicFinalize, 'item count finalization');
if (!html.includes(talentSpecGuard)) throw new Error('Missing talent specialization guard');
html = html.replaceAll(talentSpecGuard, '(p.specialization&&node.specialization&&node.specialization!==p.specialization)');
if (!html.includes(talentBranchGuard)) throw new Error('Missing talent branch guard');
html = html.replaceAll(talentBranchGuard, "p.specialization&&branch.specialization!==p.specialization?'foreign':''");
if (!html.includes(talentAvailableGuard)) throw new Error('Missing talent availability guard');
html = html.replaceAll(talentAvailableGuard, '(!p.specialization||node.specialization===p.specialization)');
requiredReplace(talentMigrationGuard, "!requestedTalents.includes(node.id)||(p.specialization&&node.specialization!==p.specialization)||node.requires&&!acceptedTalents.includes(node.requires)||node.choiceGroup&&choiceGroups.has(node.choiceGroup)", 'talent persistence migration');
requiredReplace(campaignEnergyMarker, "}if(!spendEnergy(game,1)){toast('Energía insuficiente');return;}let enemy=createEncounter(base.id,{difficulty:game.difficulty,forceElite});", 'campaign energy spending');
html = html.replaceAll('+${e.xp} EXP · +${e.gold} ORO</em>', '+${e.xp} EXP · +${e.gold} ORO · ⚡ 1</em>');
html = html.replaceAll('+${e.xp} EXP · +${e.gold} 🪙</em>', '+${e.xp} EXP · +${e.gold} 🪙 · ⚡ 1</em>');

await rm(stylesDir, { recursive: true, force: true });
await rm(scriptsDir, { recursive: true, force: true });
await mkdir(stylesDir, { recursive: true });
await mkdir(scriptsDir, { recursive: true });

let styleIndex = 0;
const styleWrites = [];
html = html.replace(/<style([^>]*)>([\s\S]*?)<\/style>/gi, (full, attrs, css) => {
  const fileName = `legacy-${String(styleIndex++).padStart(2, '0')}.css`;
  styleWrites.push(writeFile(resolve(stylesDir, fileName), css, 'utf8'));
  const media = /\bmedia=(['"])(.*?)\1/i.exec(attrs)?.[2];
  return `<link rel="stylesheet" href="/games/cryptoquest/graphics/runtime/${fileName}"${media ? ` media="${media}"` : ''}>`;
});
await Promise.all(styleWrites);

let scriptIndex = 0;
const scriptWrites = [];
html = html.replace(/<script([^>]*)>([\s\S]*?)<\/script>/gi, (full, attrs, js) => {
  if (/\bsrc\s*=/i.test(attrs)) return full;
  const type = /\btype=(['"])(.*?)\1/i.exec(attrs)?.[2]?.toLowerCase() ?? '';
  const executable = !type || type === 'text/javascript' || type === 'application/javascript' || type === 'module';
  if (!executable || !js.trim()) return full;
  const fileName = `legacy-${String(scriptIndex++).padStart(2, '0')}.js`;
  scriptWrites.push(writeFile(resolve(scriptsDir, fileName), js, 'utf8'));
  return `<script${attrs} src="/games/cryptoquest/scripts/runtime/${fileName}"></script>`;
});
await Promise.all(scriptWrites);

const presentation = [
  '<link rel="stylesheet" href="/games/cryptoquest/v27-mobile-aaa.css?v=27.0.0">',
  '<link rel="stylesheet" href="/games/cryptoquest/v28-ultra-hud.css?v=28.0.0">',
  '<link rel="stylesheet" href="/games/cryptoquest/v29-master-reference.css?v=29.0.0">',
  '<link rel="stylesheet" href="/games/cryptoquest/v30-forged-obsidian.css?v=30.0.0">',
  '<link rel="stylesheet" href="/games/cryptoquest/v32-gameplay-fixes.css?v=32.0.1">',
  '<meta name="cryptoquest-architecture" content="V5-CANONICAL">',
  '<meta name="cryptoquest-gameplay" content="V32-TALENT-ENERGY-HOME">',
].join('');
const runtime = [
  '<script src="/games/cryptoquest/v28-ultra-runtime.js?v=28.0.0" defer></script>',
  '<script src="/games/cryptoquest/v31-bootguard.js?v=31.0.0" defer></script>',
  '<script type="module" src="/games/cryptoquest/core/bootstrap.js?v=5.0.0"></script>',
].join('');

if (!html.includes('</head>') || !html.includes('</body>')) throw new Error('Runtime HTML shell is malformed');
html = html.replace('</head>', `${presentation}</head>`);
const bodyEnd = html.lastIndexOf('</body>');
html = html.slice(0, bodyEnd) + runtime + html.slice(bodyEnd);

await writeFile(runtimePath, html, 'utf8');
await mkdir(dirname(resolve(root, 'build/runtime-manifest.json')), { recursive: true });
await writeFile(resolve(root, 'build/runtime-manifest.json'), JSON.stringify({
  schema: 1,
  generatedFrom: 'data/p00.txt..p11.txt',
  runtime: 'runtime.html',
  externalizedStyles: styleIndex,
  externalizedScripts: scriptIndex,
  architecture: '5.0.0-canonical',
}, null, 2) + '\n', 'utf8');

console.log(`Generated runtime.html with ${styleIndex} external styles and ${scriptIndex} external scripts.`);
