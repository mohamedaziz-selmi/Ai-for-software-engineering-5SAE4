import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import net from 'node:net';
import { once } from 'node:events';
import { configuration, resolveRoute } from '../config.mjs';
import { createProxy, injectTag } from '../proxy.mjs';

async function serve(t, server) {
  const sockets = new Set();
  server.on('connection', socket => {
    sockets.add(socket);
    socket.on('close', () => sockets.delete(socket));
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(async () => {
    for (const socket of sockets) socket.destroy();
    if (server.listening) await new Promise(resolve => server.close(resolve));
  });
  return `http://127.0.0.1:${server.address().port}`;
}

function request(origin, path, { method = 'GET', body, headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(origin, { path, method, headers, agent: false }, res => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('error', reject);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
    });
    req.on('error', reject);
    req.end(body);
  });
}

async function echo(t, name) {
  return serve(t, http.createServer(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify({ name, method: req.method, path: req.url,
      body: Buffer.concat(chunks).toString('base64'), headers: req.headers }));
  }));
}

async function proxy(t, name, routes, timeoutMs = 1000) {
  return serve(t, createProxy({ name, routes, timeoutMs }));
}

test('configuration preserves the service boundaries and rejects loops and remote targets', () => {
  const edge = configuration('gateway', {});
  assert.equal(new Set(edge.routes.map(r => r.origin)).size, 8);
  assert.throws(() => configuration('gateway', { MARKETPLACE_ORIGIN: 'https://example.com' }));
  assert.throws(() => configuration('gateway', { MATCHER_OLLAMA_ORIGIN: 'https://example.com' }));
  assert.throws(() => configuration('gateway', { BUSINESS_AI_ORIGIN: 'https://example.com' }));
  assert.throws(() => configuration('gateway', { BUSINESS_AI_UI_ORIGIN: 'https://example.com' }));
  assert.throws(() => configuration('gateway', { CONTROL_ORIGIN: 'https://example.com' }));
  assert.ok(configuration('gateway', {}).inject && configuration('legacy', {}).inject === null && configuration('gateway', { CONTROL_BUBBLE: '0' }).inject === null);
  assert.throws(() => configuration('gateway', { AI_ORIGIN: 'https://example.com' }));
  assert.throws(() => configuration('gateway', { ADVISOR_ORIGIN: 'https://example.com' }));
  assert.throws(() => configuration('gateway', { AI_ORIGIN: 'http://127.0.0.1:8080' }));
  assert.throws(() => configuration('legacy', { FRONTEND_ORIGIN: 'http://127.0.0.1:8080' }));
  assert.throws(() => configuration('gateway', { GATEWAY_PORT: 'not-a-port' }));
});

test('routing uses path boundaries and rejects ambiguous paths', () => {
  const routes = configuration('gateway', {}).routes;
  assert.equal(resolveRoute('/api/ai/chat?q=hello%20world', routes).service, 'assistant-delivery');
  assert.equal(resolveRoute('/api/air', routes).service, 'existing-platform');
  assert.equal(resolveRoute('/assistant-extra', routes).service, 'existing-platform');
  assert.deepEqual([resolveRoute('/advisor/research/stream', routes).service, resolveRoute('/advisor/research/stream', routes).path], ['freelance-advisor', '/research/stream']);
  assert.equal(resolveRoute('/advisors', routes).service, 'existing-platform');
  for (const path of ['/api/health', '/api/match', '/api/budget']) {
    assert.deepEqual([resolveRoute(path, routes).service, resolveRoute(path, routes).path], ['marketplace-ml', path]);
  }
  assert.deepEqual([resolveRoute('/ollama-match/api/chat', routes).service, resolveRoute('/ollama-match/api/chat', routes).path], ['marketplace-matcher', '/api/chat']);
  assert.equal(resolveRoute('/ollama/api/chat', routes).service, 'existing-platform');
  assert.deepEqual([resolveRoute('/business-ai/', routes).service, resolveRoute('/business-ai/', routes).path], ['cerebro-business-ai-ui', '/']);
  assert.deepEqual([resolveRoute('/business-ai', routes).service, resolveRoute('/business-ai', routes).path], ['cerebro-business-ai-ui', '/']);
  assert.deepEqual([resolveRoute('/business-ai/assets/index.js', routes).service, resolveRoute('/business-ai/assets/index.js', routes).path], ['cerebro-business-ai-ui', '/assets/index.js']);
  assert.deepEqual([resolveRoute('/business-ai-api/api/ai/status', routes).service, resolveRoute('/business-ai-api/api/ai/status', routes).path], ['cerebro-business-ai', '/api/ai/status']);
  assert.deepEqual([resolveRoute('/_control/api/state', routes).service, resolveRoute('/_control/api/state', routes).path], ['control-center', '/api/state']);
  assert.equal(resolveRoute('/business-aix', routes).service, 'existing-platform');
  assert.equal(resolveRoute('/api/ai/status', routes).service, 'assistant-delivery');
  assert.equal(resolveRoute('/api/ai/health', routes).service, 'assistant-delivery');
  assert.equal(resolveRoute('/api/module5/health', routes).service, 'existing-platform');
  for (const path of ['//example.com', 'http://example.com', '/api/ai/../module5', '/api%2fai/chat', '/api/%252e/chat']) {
    assert.equal(resolveRoute(path, routes), null);
  }
});

test('two-hop routing preserves existing rewrites and keeps AI requests out of teammates services', async t => {
  const old = await echo(t, 'existing');
  const ai = await echo(t, 'ai');
  const oldRoutes = configuration('legacy', {}).routes.map(r => ({ ...r, origin: old }));
  const legacy = await proxy(t, 'legacy', oldRoutes);
  const edgeRoutes = configuration('gateway', {}).routes.map(r => ({ ...r,
    origin: r.service === 'existing-platform' ? legacy : ai }));
  const edge = await proxy(t, 'gateway', edgeRoutes);
  for (const [path, expected] of [
    ['/rag-api/search?q=test', '/search?q=test'], ['/sentiment-api/predict', '/predict'],
    ['/ollama/api/chat', '/api/chat'], ['/api/module5/overview', '/api/module5/overview'],
    ['/src/App.jsx', '/src/App.jsx'],
  ]) {
    const result = JSON.parse((await request(edge, path)).body);
    assert.equal(result.name, 'existing');
    assert.equal(result.path, expected);
  }
  for (const path of ['/api/ai/chat', '/assistant/', '/assistant/assets/app.js']) {
    const result = JSON.parse((await request(edge, path)).body);
    assert.equal(result.name, 'ai');
    assert.equal(result.path, path);
  }
});

test('binary uploads and authorization survive; spoofed forwarding headers do not', async t => {
  const upstream = await echo(t, 'upload');
  const edge = await proxy(t, 'gateway', [{ prefix: '/', origin: upstream, service: 'upload' }]);
  const payload = Buffer.from([0, 255, 13, 10, 128, 23]);
  const result = JSON.parse((await request(edge, '/api/ai/deliverables?version=2', {
    method: 'POST', body: payload, headers: {
      'content-type': 'application/octet-stream', authorization: 'Bearer test-only',
      'x-forwarded-for': 'attacker', forwarded: 'for=attacker',
    },
  })).body);
  assert.equal(result.method, 'POST');
  assert.equal(result.body, payload.toString('base64'));
  assert.equal(result.headers.authorization, 'Bearer test-only');
  assert.equal(result.headers['x-forwarded-for'], undefined);
  assert.equal(result.headers.forwarded, undefined);
});

test('upstream error status and multiple cookies pass through without automatic retries', async t => {
  let calls = 0;
  const upstream = await serve(t, http.createServer((req, res) => {
    calls++;
    res.writeHead(429, { 'retry-after': '3', 'set-cookie': ['one=1; Path=/', 'two=2; Path=/'] });
    res.end('quota');
  }));
  const edge = await proxy(t, 'gateway', [{ prefix: '/', origin: upstream, service: 'api' }]);
  const result = await request(edge, '/api/ai/review', { method: 'POST', body: '{}' });
  assert.equal(result.status, 429);
  assert.equal(result.headers['retry-after'], '3');
  assert.equal(result.headers['set-cookie'].length, 2);
  assert.equal(calls, 1);
});

test('gateway streams the first event before the upstream ends', async t => {
  let release;
  const upstream = await serve(t, http.createServer((req, res) => {
    res.writeHead(200, { 'content-type': 'text/event-stream' });
    res.write('data: first\n\n');
    release = () => res.end('data: last\n\n');
  }));
  const edge = await proxy(t, 'gateway', [{ prefix: '/', origin: upstream, service: 'chat' }]);
  await new Promise((resolve, reject) => {
    const req = http.get(`${edge}/api/ai/chat`, res => {
      let body = '';
      res.on('data', chunk => { body += chunk; if (body.includes('first')) release(); });
      res.on('end', () => { assert.match(body, /first[\s\S]*last/); resolve(); });
      res.on('error', reject);
    });
    req.setTimeout(2000, () => req.destroy(new Error('Streaming was buffered')));
    req.on('error', reject);
  });
});

test('unavailable AI returns 502 while existing platform continues working', async t => {
  const closed = http.createServer();
  const deadOrigin = await serve(t, closed);
  await new Promise(resolve => closed.close(resolve));
  const old = await echo(t, 'existing');
  const edge = await proxy(t, 'gateway', [
    { prefix: '/api/ai', origin: deadOrigin, service: 'assistant-delivery' },
    { prefix: '/', origin: old, service: 'existing-platform' },
  ]);
  const failure = await request(edge, '/api/ai/chat');
  assert.equal(failure.status, 502);
  assert.equal(JSON.parse(failure.body).service, 'assistant-delivery');
  assert.equal((await request(edge, '/')).status, 200);
  const health = JSON.parse((await request(edge, '/_gateway/health')).body);
  assert.equal(health.upstreamsChecked, false);
});

test('idle upstream returns 504', async t => {
  const upstream = await serve(t, http.createServer(() => {}));
  const edge = await proxy(t, 'gateway', [{ prefix: '/', origin: upstream, service: 'slow' }], 50);
  assert.equal((await request(edge, '/api/ai/review')).status, 504);
});

test('WebSocket upgrade and bytes traverse both proxy layers', async t => {
  const upstream = http.createServer();
  upstream.on('upgrade', (req, socket, head) => {
    socket.write('HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n');
    if (head.length) socket.write(head);
    socket.on('data', data => socket.write(data));
    socket.on('error', () => {});
  });
  const target = await serve(t, upstream);
  const legacy = await proxy(t, 'legacy', [{ prefix: '/', origin: target, service: 'vite' }]);
  const edge = await proxy(t, 'gateway', [{ prefix: '/', origin: legacy, service: 'existing-platform' }]);
  const socket = net.connect(Number(new URL(edge).port), '127.0.0.1');
  t.after(() => socket.destroy());
  await once(socket, 'connect');
  await new Promise((resolve, reject) => {
    let accumulated = Buffer.alloc(0);
    let upgraded = false;
    socket.setTimeout(2000, () => socket.destroy(new Error('WebSocket timeout')));
    socket.on('error', reject);
    socket.on('data', data => {
      accumulated = Buffer.concat([accumulated, data]);
      if (!upgraded && accumulated.includes('\r\n\r\n')) {
        assert.match(accumulated.toString(), /^HTTP\/1.1 101/);
        upgraded = true;
        accumulated = Buffer.alloc(0);
        socket.write(Buffer.from([0x81, 0x02, 0x6f, 0x6b]));
      } else if (upgraded && accumulated.length >= 4) {
        assert.deepEqual(accumulated, Buffer.from([0x81, 0x02, 0x6f, 0x6b]));
        resolve();
      }
    });
    socket.write('GET /?token=test HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\n\r\n');
  });
  socket.destroy();
});


test('the control bubble is added to HTML pages only, with a corrected length', async t => {
  const tag = '<script src="/_control/bubble.js" async data-control-base="/_control"></script>';
  assert.equal(injectTag('<html><body><p>x</p></body></html>', tag), `<html><body><p>x</p>${tag}</body></html>`);
  assert.equal(injectTag('<div id="root"></div>', tag), `<div id="root"></div>${tag}`);
  assert.equal(injectTag(`<body>${tag}</body>`, tag), `<body>${tag}</body>`);
  const page = await serve(t, http.createServer((req, res) => {
    if (req.url === '/api') { res.setHeader('content-type', 'application/json'); return res.end('{"ok":true}'); }
    if (req.url === '/gz') { res.setHeader('content-type', 'text/html'); res.setHeader('content-encoding', 'gzip'); return res.end('zz'); }
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.end('<html><body>hi</body></html>');
  }));
  const edge = await proxy(t, 'gateway', [{ prefix: '/', origin: page, service: 'existing-platform' }]);
  const injecting = await serve(t, createProxy({ name: 'gateway', routes: [{ prefix: '/', origin: page, service: 'existing-platform' }],
    timeoutMs: 1000, inject: { tag, skipService: 'control-center' } }));
  const html = await request(injecting, '/');
  assert.equal(html.body.toString(), `<html><body>hi${tag}</body></html>`);
  assert.equal(Number(html.headers['content-length']), html.body.length);
  assert.equal((await request(injecting, '/api')).body.toString(), '{"ok":true}');
  assert.equal((await request(injecting, '/gz')).body.toString(), 'zz');
  assert.equal((await request(edge, '/')).body.toString(), '<html><body>hi</body></html>');
});

