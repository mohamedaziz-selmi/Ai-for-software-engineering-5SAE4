import http from 'node:http';
import { resolveRoute } from './config.mjs';

function filteredHeaders(headers) {
  const blocked = new Set(['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailer', 'transfer-encoding', 'upgrade',
    ...String(headers.connection || '').toLowerCase().split(',').map(v => v.trim())]);
  return Object.fromEntries(Object.entries(headers).filter(([key]) => !blocked.has(key.toLowerCase())));
}

function requestHeaders(req, route, upgrade = false) {
  const headers = filteredHeaders(req.headers);
  // These headers are not an authentication mechanism. Do not trust client-supplied forwarding metadata.
  for (const key of Object.keys(headers)) {
    if (key === 'forwarded' || key.startsWith('x-forwarded-')) delete headers[key];
  }
  headers.host = new URL(route.origin).host;
  if (upgrade) {
    headers.connection = 'Upgrade';
    headers.upgrade = req.headers.upgrade;
  }
  return headers;
}

// Adds the control center's bubble to a full HTML page: only GET 200 text/html, uncompressed, not the control
// center's own pages. The page is buffered (up to 5 MB) so its length can be corrected; anything else streams.
const INJECT_LIMIT = 5 * 1024 * 1024;
function injectable(config, req, reply, route) {
  const type = String(reply.headers['content-type'] || '').toLowerCase();
  return Boolean(config.inject) && req.method === 'GET' && reply.statusCode === 200 && route.service !== config.inject.skipService
    && type.startsWith('text/html') && !reply.headers['content-encoding'];
}

export function injectTag(html, tag) {
  if (html.includes('data-control-base=')) return html;
  const at = html.toLowerCase().lastIndexOf('</body>');
  return at < 0 ? html + tag : html.slice(0, at) + tag + html.slice(at);
}

function json(res, status, data) {
  if (res.destroyed || res.writableEnded) return;
  if (res.headersSent) return res.destroy();
  res.writeHead(status, { 'content-type': 'application/json', 'cache-control': 'no-store' });
  res.end(JSON.stringify(data));
}

export function createProxy(config) {
  const upgradedSockets = new Set();
  const server = http.createServer((req, res) => {
    if (req.url === '/_gateway/health' && config.name === 'gateway') {
      if (!['GET', 'HEAD'].includes(req.method)) return json(res, 405, { error: 'method_not_allowed' });
      return json(res, 200, { service: 'gateway', status: 'up', upstreamsChecked: false });
    }
    const route = resolveRoute(req.url, config.routes);
    if (!route) return json(res, 400, { error: 'invalid_request_path' });
    const upstream = http.request(route.origin, {
      method: req.method, path: route.path, headers: requestHeaders(req, route), agent: false,
    });
    upstream.setTimeout(config.timeoutMs, () => {
      json(res, 504, { error: 'upstream_timeout', service: route.service });
      upstream.destroy();
    });
    upstream.on('error', () => json(res, 502, { error: 'upstream_unavailable', service: route.service }));
    upstream.on('response', reply => {
      if (res.destroyed) return reply.destroy();
      if (injectable(config, req, reply, route)) {
        const chunks = [];
        let size = 0;
        reply.on('data', chunk => { size += chunk.length; chunks.push(chunk); });
        reply.on('error', () => res.destroy());
        reply.on('end', () => {
          const original = Buffer.concat(chunks);
          const body = size > INJECT_LIMIT ? original : Buffer.from(injectTag(original.toString('utf8'), config.inject.tag), 'utf8');
          const headers = filteredHeaders(reply.headers);
          delete headers['content-length'];
          headers['content-length'] = String(body.length);
          if (!res.destroyed) { res.writeHead(reply.statusCode, headers); res.end(body); }
        });
        return;
      }
      res.writeHead(reply.statusCode, filteredHeaders(reply.headers));
      res.flushHeaders();
      reply.on('error', () => res.destroy());
      reply.pipe(res);
    });
    req.on('aborted', () => upstream.destroy());
    req.on('error', () => upstream.destroy());
    res.on('close', () => { if (!res.writableFinished) upstream.destroy(); });
    req.pipe(upstream);
  });

  // Vite's development WebSocket must continue through both proxy layers.
  server.on('upgrade', (req, socket, head) => {
    socket.on('error', () => socket.destroy());
    const route = resolveRoute(req.url, config.routes);
    if (!route || req.headers.upgrade?.toLowerCase() !== 'websocket') {
      socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n');
      return;
    }
    const upstream = http.request(route.origin, {
      method: 'GET', path: route.path, headers: requestHeaders(req, route, true), agent: false,
    });
    const timer = setTimeout(() => upstream.destroy(), config.timeoutMs);
    upstream.on('error', () => {
      clearTimeout(timer);
      if (!socket.destroyed) socket.end('HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n');
    });
    upstream.on('response', reply => {
      clearTimeout(timer);
      reply.resume();
      socket.end(`HTTP/1.1 ${reply.statusCode} Upgrade Rejected\r\nConnection: close\r\n\r\n`);
    });
    upstream.on('upgrade', (reply, remote, remoteHead) => {
      clearTimeout(timer);
      if (socket.destroyed) return remote.destroy();
      const headers = filteredHeaders(reply.headers);
      headers.connection = 'Upgrade';
      headers.upgrade = 'websocket';
      socket.write(`HTTP/1.1 101 Switching Protocols\r\n${Object.entries(headers).map(([k, v]) => `${k}: ${v}`).join('\r\n')}\r\n\r\n`);
      if (remoteHead.length) socket.write(remoteHead);
      if (head.length) remote.write(head);
      upgradedSockets.add(socket);
      socket.on('close', () => { upgradedSockets.delete(socket); remote.destroy(); });
      remote.on('close', () => socket.destroy());
      remote.on('error', () => socket.destroy());
      socket.pipe(remote).pipe(socket);
    });
    socket.on('close', () => { clearTimeout(timer); upstream.destroy(); });
    upstream.end();
  });
  server.shutdown = () => {
    for (const socket of upgradedSockets) socket.destroy();
    server.closeAllConnections();
    return new Promise(resolve => server.close(resolve));
  };
  return server;
}
