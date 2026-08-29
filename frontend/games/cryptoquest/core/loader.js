async function loadCanonicalRuntime() {
  const response = await fetch('/games/cryptoquest/runtime.html', { cache: 'no-store' });
  if (!response.ok) throw new Error(`runtime.html: ${response.status}`);
  let html = await response.text();
  html = html.replace('/games/cryptoquest/v32-gameplay-fixes.css?v=32.0.1','/games/cryptoquest/v32-gameplay-fixes.css?v=32.0.3');
  if (!html.includes('/games/cryptoquest/v33-anime-premium.css?v=33.0.0')) {
    html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v33-anime-premium.css?v=33.0.0"><meta name="cryptoquest-visual" content="V33-ANIME-PREMIUM"></head>');
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
