async function loadCanonicalRuntime() {
  const response = await fetch('/games/cryptoquest/runtime.html', { cache: 'no-store' });
  if (!response.ok) throw new Error(`runtime.html: ${response.status}`);
  let html = await response.text();

  // V38 clean-slate presentation: retire the stacked V27–V37 visual layers at load time
  // without touching canonical gameplay/state/persistence code or deleting the checkpointed files.
  html = html.replace(/<link[^>]+href="\/games\/cryptoquest\/v(?:27|28|29|30|32|33|34|35|36|37)[^"]*"[^>]*>/gi, '');
  html = html.replace(/<script[^>]+src="\/games\/cryptoquest\/v(?:34|35|36|37)[^"]*"[^>]*><\/script>/gi, '');
  html = html.replace(/<meta[^>]+name="cryptoquest-(?:visual|cinematic|premium-layout|risk-rebuild|hero-hub)"[^>]*>/gi, '');

  html = html.replace('</head>', '<link rel="stylesheet" href="/games/cryptoquest/v38-total-rebuild.css?v=38.0.1"><link rel="stylesheet" href="/games/cryptoquest/v38-total-rebuild-hotfix.css?v=38.0.1"><meta name="cryptoquest-interface" content="V38-TOTAL-REBUILD"></head>');
  html = html.replace('</body>', '<script src="/games/cryptoquest/v38-total-rebuild.js?v=38.0.1" defer></script></body>');

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
