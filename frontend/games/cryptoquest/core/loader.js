async function loadCanonicalRuntime() {
  const response = await fetch('/games/cryptoquest/runtime.html', { cache: 'no-store' });
  if (!response.ok) throw new Error(`runtime.html: ${response.status}`);
  let html = await response.text();
  html = html.replace('/games/cryptoquest/v32-gameplay-fixes.css?v=32.0.1','/games/cryptoquest/v32-gameplay-fixes.css?v=32.0.3');
  if (!html.includes('/games/cryptoquest/v33-anime-premium.css?v=33.0.0')) {
    html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v33-anime-premium.css?v=33.0.0"><meta name="cryptoquest-visual" content="V33-ANIME-PREMIUM"></head>');
  }
  if (!html.includes('/games/cryptoquest/v34-cinematic-anime.css?v=34.0.0')) {
    html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v34-cinematic-anime.css?v=34.0.0"><link rel="stylesheet" href="/games/cryptoquest/v34-cinematic-hotfix.css?v=34.2.2"><meta name="cryptoquest-cinematic" content="V34-CINEMATIC-ANIME"></head>');
  }
  if (!html.includes('/games/cryptoquest/v35-premium-layout.css?v=35.0.0')) {
    html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v35-premium-layout.css?v=35.0.0"><meta name="cryptoquest-premium-layout" content="V35-PREMIUM-MOBILE"></head>');
  }
  if (!html.includes('/games/cryptoquest/v36-risk-rebuild.css?v=36.0.0')) {
    html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v36-risk-rebuild.css?v=36.0.0"><meta name="cryptoquest-risk-rebuild" content="V36-RISK-REBUILD"></head>');
  }
  if (!html.includes('/games/cryptoquest/v37-hero-hub.css?v=37.0.0')) {
    html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v37-hero-hub.css?v=37.0.0"><link rel="stylesheet" href="/games/cryptoquest/v37-hero-hub-hotfix.css?v=37.0.1"><meta name="cryptoquest-hero-hub" content="V37-HERO-HUB"></head>');
  }
  if (!html.includes('/games/cryptoquest/v34-cinematic-runtime.js?v=34.2.2')) {
    html = html.replace('</body>', '<script src="/games/cryptoquest/v34-cinematic-runtime.js?v=34.2.2" defer></script></body>');
  }
  if (!html.includes('/games/cryptoquest/v35-premium-runtime.js?v=35.0.1')) {
    html = html.replace('</body>', '<script src="/games/cryptoquest/v35-premium-runtime.js?v=35.0.1" defer></script></body>');
  }
  if (!html.includes('/games/cryptoquest/v36-risk-runtime.js?v=36.0.0')) {
    html = html.replace('</body>', '<script src="/games/cryptoquest/v36-risk-runtime.js?v=36.0.0" defer></script></body>');
  }
  if (!html.includes('/games/cryptoquest/v37-hero-hub-runtime.js?v=37.0.0')) {
    html = html.replace('</body>', '<script src="/games/cryptoquest/v37-hero-hub-runtime.js?v=37.0.0" defer></script></body>');
  }
  if (!html.includes('V5-CANONICAL') || !html.includes('core/bootstrap.js?v=5.0.0')) {
    throw new Error('CryptoQuest canonical runtime markers are missing');
  }
  if (html.includes('DecompressionStream') || html.includes('data/p00.txt')) {
    throw new Error('CryptoQuest canonical runtime unexpectedly references the retired packed source');
  }
  return html;
}

(async () => {
  try {
    const html = await loadCanonicalRuntime();
    document.open();
    document.write(html);
    document.close();
  } catch (error) {
    const element = document.getElementById('err');
    if (element) element.textContent = `No se pudo cargar CryptoQuest: ${error.message}`;
    console.error(error);
  }
})();
