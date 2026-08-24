const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      ...SECURITY_HEADERS,
      ...extraHeaders,
    },
  });
}

function normalizeOrigin(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' && url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') {
      return null;
    }
    return url.origin;
  } catch {
    return null;
  }
}

async function proxyApi(request, env) {
  const origin = normalizeOrigin(env.API_ORIGIN);
  if (!origin) {
    return json({
      ok: false,
      code: 'API_NOT_CONFIGURED',
      message: 'Los servicios online todavía no están conectados en este entorno.',
    }, 503);
  }

  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin);
  const headers = new Headers(request.headers);
  headers.set('X-CFS-Edge', 'cloudflare-worker');
  headers.delete('host');

  try {
    const upstream = await fetch(new Request(target.toString(), {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      redirect: 'manual',
    }));

    const responseHeaders = new Headers(upstream.headers);
    for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
      if (!responseHeaders.has(key)) responseHeaders.set(key, value);
    }
    responseHeaders.set('Cache-Control', 'no-store');

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return json({
      ok: false,
      code: 'API_UPSTREAM_UNAVAILABLE',
      message: 'El servicio online no está disponible temporalmente.',
    }, 502);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return json({ ok: true, service: 'cfs-edge', api_configured: Boolean(normalizeOrigin(env.API_ORIGIN)) });
    }

    if (url.pathname === '/ready') {
      const configured = Boolean(normalizeOrigin(env.API_ORIGIN));
      return json({ ok: configured, service: 'cfs-edge', api_configured: configured }, configured ? 200 : 503);
    }

    if (url.pathname.startsWith('/api/')) {
      return proxyApi(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
