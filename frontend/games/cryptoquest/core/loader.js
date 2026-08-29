async function loadCanonicalRuntime() {
  const response = await fetch('/games/cryptoquest/runtime.html', { cache: 'no-store' });
  if (!response.ok) throw new Error(`runtime.html: ${response.status}`);
  const html = await response.text();
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
