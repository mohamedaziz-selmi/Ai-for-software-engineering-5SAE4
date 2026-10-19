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
  const advisorOrigin = origin(env.ADVISOR_ORIGIN, 'http://127.0.0.1:8004');
  const marketplaceOrigin = origin(env.MARKETPLACE_ORIGIN, 'http://127.0.0.1:8005');
  const matcherOrigin = origin(env.MATCHER_OLLAMA_ORIGIN, 'http://127.0.0.1:11436');
  const businessAiOrigin = origin(env.BUSINESS_AI_ORIGIN, 'http://127.0.0.1:8900');
  const businessAiUiOrigin = origin(env.BUSINESS_AI_UI_ORIGIN, 'http://127.0.0.1:8905');
  const controlOrigin = origin(env.CONTROL_ORIGIN, 'http://127.0.0.1:8090');
  const legacyOrigin = origin(env.LEGACY_ORIGIN, `http://127.0.0.1:${legacyPort}`);
  const frontendOrigin = origin(env.FRONTEND_ORIGIN, 'http://127.0.0.1:8766');
  const routes = mode === 'gateway' ? [
    { prefix: '/api/ai', origin: aiOrigin, service: 'assistant-delivery' },
    { prefix: '/assistant', origin: aiOrigin, service: 'assistant-delivery' },
    // agentic-freelance-advisor (FastAPI): the frontend calls /advisor/health and /advisor/research/stream.
    { prefix: '/advisor', origin: advisorOrigin, strip: true, service: 'freelance-advisor' },
    // marketplace_ml (FastAPI): only its own endpoints, so /api/ai and /api/module5 are not captured.
    { prefix: '/api/health', origin: marketplaceOrigin, service: 'marketplace-ml' },
    { prefix: '/api/match', origin: marketplaceOrigin, service: 'marketplace-ml' },
    { prefix: '/api/budget', origin: marketplaceOrigin, service: 'marketplace-ml' },
    // marketplace_ml matcher: Qwen2.5 0.5B on its own CPU-only Ollama (the frontend calls /ollama-match/api/...).
    { prefix: '/ollama-match', origin: matcherOrigin, strip: true, service: 'marketplace-matcher' },
    // cerebro_business_ai, its own microservice: its screens (:8905) under /business-ai/, its gateway (:8900) under
    // /business-ai-api (its API paths start with /api/ai, the assistant module's prefix here). Prefixes are removed.
    { prefix: '/business-ai', origin: businessAiUiOrigin, strip: true, service: 'cerebro-business-ai-ui' },
    { prefix: '/business-ai-api', origin: businessAiOrigin, strip: true, service: 'cerebro-business-ai' },
    // control_center (owner's microservice): its API and the floating bubble's script, under /_control.
    { prefix: '/_control', origin: controlOrigin, strip: true, service: 'control-center' },
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
  // In gateway mode every HTML page gets the control center's bubble (CONTROL_BUBBLE=0 turns it off).
  const inject = mode === 'gateway' && env.CONTROL_BUBBLE !== '0'
    ? { tag: '<script src="/_control/bubble.js" async data-control-base="/_control"></script>', skipService: 'control-center' } : null;
  return {
    name: mode, host: '127.0.0.1', port, routes, inject,
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
