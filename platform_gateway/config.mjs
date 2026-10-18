function integer(value, fallback, name, max = 65535) {
  const number = value === undefined ? fallback : Number(value);
  if (!Number.isInteger(number) || number < 1 || number > max) {
    throw new Error(`Invalid ${name}`);
  }
  return number;
}

function origin(value, fallback) {
  const url = new URL(value || fallback);
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
      || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Upstreams must be local HTTP origins without credentials, paths or query strings');
  }
  return url.origin;
}

export function configuration(mode, env = process.env) {
  if (!['gateway', 'legacy'].includes(mode)) throw new Error('Use gateway or legacy');
  const gatewayPort = integer(env.GATEWAY_PORT, 8080, 'GATEWAY_PORT');
  const legacyPort = integer(env.LEGACY_PORT, 8081, 'LEGACY_PORT');
  const aiOrigin = origin(env.AI_ORIGIN, 'http://127.0.0.1:8003');
  const legacyOrigin = origin(env.LEGACY_ORIGIN, `http://127.0.0.1:${legacyPort}`);
  const frontendOrigin = origin(env.FRONTEND_ORIGIN, 'http://127.0.0.1:8766');
  const routes = mode === 'gateway' ? [
    { prefix: '/api/ai', origin: aiOrigin, service: 'assistant-delivery' },
    { prefix: '/assistant', origin: aiOrigin, service: 'assistant-delivery' },
    { prefix: '/', origin: legacyOrigin, service: 'existing-platform' },
  ] : [
    { prefix: '/ollama', origin: origin(env.OLLAMA_ORIGIN, 'http://127.0.0.1:11434'), strip: true, service: 'existing-ollama' },
    { prefix: '/rag-api', origin: origin(env.RAG_ORIGIN, 'http://127.0.0.1:8000'), strip: true, service: 'existing-retrieval' },
    { prefix: '/sentiment-api', origin: origin(env.SENTIMENT_ORIGIN, 'http://127.0.0.1:8001'), strip: true, service: 'existing-sentiment' },
    { prefix: '/api/module5', origin: origin(env.BI_ORIGIN, 'http://127.0.0.1:8002'), service: 'existing-bi' },
    { prefix: '/', origin: frontendOrigin, service: 'existing-frontend' },
  ];
  const port = mode === 'gateway' ? gatewayPort : legacyPort;
  if (gatewayPort === legacyPort) throw new Error('Gateway and legacy ports must differ');
  for (const route of routes) {
    const destinationPort = Number(new URL(route.origin).port || 80);
    if (destinationPort === port || (mode === 'legacy' && destinationPort === gatewayPort)) {
      throw new Error('Upstream configuration creates a proxy loop');
    }
  }
  return {
    name: mode, host: '127.0.0.1', port, routes,
    timeoutMs: integer(env.UPSTREAM_IDLE_TIMEOUT_MS, 120000, 'UPSTREAM_IDLE_TIMEOUT_MS', 3600000),
  };
}

export function resolveRoute(rawPath, routes) {
  // Reject ambiguous path forms rather than letting two proxy layers route them differently.
  if (!rawPath?.startsWith('/') || rawPath.startsWith('//') || /[\\\r\n#]/.test(rawPath)) return null;
  const index = rawPath.indexOf('?');
  const pathname = index < 0 ? rawPath : rawPath.slice(0, index);
  const query = index < 0 ? '' : rawPath.slice(index);
  if (/%(?:2f|5c|2e|25)/i.test(pathname) || /\/(?:\.|\.\.)(?:\/|$)/.test(pathname)) return null;
  const route = routes.find(r => r.prefix === '/' || pathname === r.prefix || pathname.startsWith(`${r.prefix}/`));
  if (!route) return null;
  return { ...route, path: (route.strip ? pathname.slice(route.prefix.length) || '/' : pathname) + query };
}
