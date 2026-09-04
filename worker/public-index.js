import legacyWorker from './index.js';

const DEFAULT_FEATURES = Object.freeze({
  cryptoquest_enabled: false,
  crypto_factory_game_enabled: false,
});

let featureCache = { expiresAt: 0, value: DEFAULT_FEATURES };

function normalizeOrigin(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' && url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') return null;
    return url.origin;
  } catch {
    return null;
  }
}

async function loadFeatures(env) {
  const now = Date.now();
  if (featureCache.expiresAt > now) return featureCache.value;
  const origin = normalizeOrigin(env.API_ORIGIN);
  if (!origin) return DEFAULT_FEATURES;
  try {
    const response = await fetch(new URL('/api/v1/platform/features', origin), {
      headers: { 'Accept': 'application/json', 'X-CFS-Edge': 'cloudflare-worker' },
      cf: { cacheTtl: 0, cacheEverything: false },
    });
    if (!response.ok) throw new Error(`feature status ${response.status}`);
    const payload = await response.json();
    const flags = payload?.features || {};
    const value = {
      cryptoquest_enabled: flags.cryptoquest_enabled === true,
      crypto_factory_game_enabled: flags.crypto_factory_game_enabled === true,
    };
    featureCache = { expiresAt: now + 5000, value };
    return value;
  } catch {
    featureCache = { expiresAt: now + 2000, value: DEFAULT_FEATURES };
    return DEFAULT_FEATURES;
  }
}

function hiddenGameForUrl(url, features) {
  const path = url.pathname.toLowerCase();
  const slug = (url.searchParams.get('slug') || '').toLowerCase();
  if (!features.cryptoquest_enabled) {
    if (path === '/cryptoquest' || path.startsWith('/cryptoquest/') || path.startsWith('/games/cryptoquest') || slug === 'cryptoquest-rpg' || slug === 'cryptoquest') return 'cryptoquest';
    if (path.startsWith('/play/cryptoquest')) return 'cryptoquest';
  }
  if (!features.crypto_factory_game_enabled) {
    if (path === '/crypto-factory-game' || path.startsWith('/crypto-factory-game/') || path.startsWith('/games/crypto-factory') || slug === 'crypto-factory' || slug === 'crypto-factory-game') return 'crypto_factory_game';
    if (path.startsWith('/play/crypto-factory')) return 'crypto_factory_game';
  }
  return null;
}

function disabledResponse() {
  return new Response('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><title>Not found</title></head><body><h1>404</h1></body></html>', {
    status: 404,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Robots-Tag': 'noindex, nofollow',
      'X-Content-Type-Options': 'nosniff',
    },
  });
}

function isFirstPartyHiddenGame(game, features) {
  const slug = String(game?.slug || '').toLowerCase();
  const title = String(game?.title || '').toLowerCase();
  if (!features.cryptoquest_enabled && (slug === 'cryptoquest-rpg' || slug === 'cryptoquest' || title === 'cryptoquest rpg')) return true;
  if (!features.crypto_factory_game_enabled && (slug === 'crypto-factory' || slug === 'crypto-factory-game' || title === 'crypto factory')) return true;
  return false;
}

function isHiddenGameProduct(product, features) {
  const id = String(product?.product_id || '').toLowerCase();
  const label = String(product?.label || '').toLowerCase();
  const entitlement = String(product?.entitlement_key || '').toLowerCase();
  if (!features.cryptoquest_enabled && (id.startsWith('cryptoquest_') || label.includes('cryptoquest') || entitlement.startsWith('cryptoquest_'))) return true;
  if (!features.crypto_factory_game_enabled && (id.startsWith('crypto_factory_game_') || label === 'crypto factory' || entitlement.startsWith('crypto_factory_game:'))) return true;
  return false;
}

async function filterJsonArray(response, field, predicate) {
  if (!response.ok) return response;
  const type = (response.headers.get('content-type') || '').toLowerCase();
  if (!type.includes('application/json')) return response;
  try {
    const payload = await response.json();
    if (Array.isArray(payload?.[field])) payload[field] = payload[field].filter(item => !predicate(item));
    const headers = new Headers(response.headers);
    headers.delete('content-length');
    headers.set('Cache-Control', 'no-store');
    return new Response(JSON.stringify(payload), { status: response.status, statusText: response.statusText, headers });
  } catch {
    return response;
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const features = await loadFeatures(env);

    if (hiddenGameForUrl(url, features)) return disabledResponse();

    if ((!features.cryptoquest_enabled || !features.crypto_factory_game_enabled) && (url.pathname === '/browser-games' || url.pathname === '/browser-games.html')) {
      return disabledResponse();
    }

    const response = await legacyWorker.fetch(request, env, ctx);

    if (request.method === 'GET' && url.pathname === '/api/v1/games') {
      return filterJsonArray(response, 'games', game => isFirstPartyHiddenGame(game, features));
    }
    if (request.method === 'GET' && url.pathname === '/api/v1/products') {
      return filterJsonArray(response, 'products', product => isHiddenGameProduct(product, features));
    }

    return response;
  },
};
