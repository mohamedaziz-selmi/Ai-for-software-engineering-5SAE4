// Control center: a small local microservice that shows the platform's architecture and live state, and starts or
// stops each module (with the model it needs). Node.js standard library only. Listens on 127.0.0.1:8090.
//
//   node control_center/server.mjs          (or START_PLATFORM.cmd, which also starts the front end)
//
// Safety: loopback only; state-changing calls need POST + the X-Control header from a local origin; a process is
// stopped only if it owns the expected port AND its command line matches the registry (see registry.mjs).
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { COMPONENTS, MODULES, RUNTIMES } from './registry.mjs';
import { descendants, gpu, killTree, listeningPorts, ollama, processes, systemLoad, unloadModel } from './system.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const PUBLIC = path.join(HERE, 'public');
const LOGS = path.join(HERE, 'logs');
const PORT = Number(process.env.CONTROL_PORT || 8090);
const POLL_MS = 3000;
fs.mkdirSync(LOGS, { recursive: true });

const abs = p => path.resolve(ROOT, p);
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ------------------------------------------------------------------ live snapshot (refreshed in the background)
let snapshot = { ports: new Map(), procs: new Map(), gpu: null, load: systemLoad(), runtimes: {}, at: 0 };
let prevCpu = new Map();
const spawned = new Map(); // component id -> pid of the process this control center started
const busy = new Map();    // module id -> 'starting' | 'stopping'
const notes = new Map();   // module id -> last message for the user

async function refresh() {
  const [ports, procs, g] = await Promise.all([listeningPorts(), processes(), gpu()]);
  const runtimes = {};
  await Promise.all(RUNTIMES.map(async r => { runtimes[r.id] = ports.has(r.port) ? await ollama(r.port) : null; }));
  const elapsed = (Date.now() - (snapshot.at || Date.now() - POLL_MS)) / 1000;
  const cores = snapshot.load.cores || 1;
  for (const p of procs.values()) {
    const before = prevCpu.get(p.pid);
    p.cpu = before === undefined ? 0 : Math.max(0, (100 * (p.cpuTime - before)) / Math.max(0.5, elapsed) / cores);
  }
  prevCpu = new Map([...procs.values()].map(p => [p.pid, p.cpuTime]));
  snapshot = { ports, procs, gpu: g, load: systemLoad(), runtimes, at: Date.now() };
}

const portsOf = c => c.ports || [c.port];
const isUp = id => portsOf(COMPONENTS[id]).every(p => snapshot.ports.has(p));
const missing = id => (COMPONENTS[id].requires || []).filter(f => !fs.existsSync(abs(f)));

function componentState(id) {
  const c = COMPONENTS[id];
  const pids = portsOf(c).map(p => snapshot.ports.get(p)).filter(Boolean);
  const tree = [...new Set(pids.flatMap(pid => descendants(snapshot.procs, pid)))];
  const ps = tree.map(pid => snapshot.procs.get(pid)).filter(Boolean);
  return {
    id, name: c.name, ports: portsOf(c), up: isUp(id), partial: pids.length > 0 && !isUp(id), missing: missing(id),
    ramMb: Math.round(ps.reduce((a, p) => a + p.rss, 0) / 2 ** 20), cpu: Math.round(ps.reduce((a, p) => a + (p.cpu || 0), 0) * 10) / 10,
  };
}

// The dashboard's chat uses llama3.2:3b when installed, otherwise the first model the shared Ollama lists (src/App.jsx).
function chatModel() {
  const installed = snapshot.runtimes['shared-ollama']?.installed || [];
  return installed.includes('llama3.2:3b') ? 'llama3.2:3b' : installed[0] || null;
}

function runningModules() {
  return MODULES.filter(m => m.components.length ? m.components.every(isUp) : (m.uses || []).every(isUp));
}

function moduleState(m) {
  const components = m.components.map(componentState);
  const uses = (m.uses || []).map(componentState);
  const notSetUp = [...components, ...uses].flatMap(c => c.missing);
  const all = components.length ? components : uses;
  const upCount = all.filter(c => c.up).length;
  let status = upCount === all.length ? 'on' : upCount || all.some(c => c.partial) ? 'partial' : 'off';
  if (busy.has(m.id)) status = busy.get(m.id);
  else if (notSetUp.length && status === 'off') status = 'not_set_up';
  // Models: what the module needs, whether its runtime has it, and VRAM held by it right now.
  const models = [];
  const vramFrom = (runtimeId, names) => {
    const rt = snapshot.runtimes[runtimeId];
    for (const name of names) {
      models.push({ name, runtime: COMPONENTS[runtimeId].port, installed: rt ? rt.installed.includes(name) : null,
        loaded: rt ? rt.loaded.some(l => l.name === name) : false, vramMb: rt?.loaded.find(l => l.name === name)?.vramMb || 0 });
    }
  };
  for (const id of m.components.filter(id => COMPONENTS[id].runtime)) {
    const rt = snapshot.runtimes[id];
    for (const l of rt?.loaded || []) models.push({ name: l.name, runtime: COMPONENTS[id].port, installed: true, loaded: true, vramMb: l.vramMb });
  }
  if (m.id === 'chat') vramFrom('shared-ollama', [chatModel()].filter(Boolean));
  else if (m.models) vramFrom('shared-ollama', m.models);
  return {
    id: m.id, name: m.name, role: m.role, url: m.url || null, owner: Boolean(m.owner), status, note: notes.get(m.id) || null,
    notSetUp, components, uses: uses.map(u => ({ id: u.id, name: u.name, up: u.up, ports: u.ports })), models,
    ramMb: components.reduce((a, c) => a + c.ramMb, 0), cpu: Math.round(components.reduce((a, c) => a + c.cpu, 0) * 10) / 10,
    vramMb: models.reduce((a, x) => a + (x.vramMb || 0), 0),
  };
}

function state() {
  const g = snapshot.gpu;
  return {
    at: snapshot.at, control: { port: PORT },
    system: {
      cpu: snapshot.load.cpu === null ? null : Math.round(snapshot.load.cpu), ram: Math.round(snapshot.load.ram), ramTotalGb: Math.round(snapshot.load.ramTotalGb),
      gpu: g && { name: g.name, temp: g.temp, util: g.util, vramUsedMb: g.vramUsed, vramTotalMb: g.vramTotal },
    },
    runtimes: RUNTIMES.map(r => ({ id: r.id, port: r.port, up: snapshot.ports.has(r.port), loaded: snapshot.runtimes[r.id]?.loaded || [] })),
    modules: MODULES.map(moduleState),
  };
}

// ------------------------------------------------------------------ actions
function resolveCmd(cmd) {
  if (cmd.includes('/') || cmd.includes('\\')) return abs(cmd);
  if (cmd === 'ollama') {
    const local = path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Ollama', 'ollama.exe');
    if (fs.existsSync(local)) return local;
  }
  return cmd;
}

function envFor(c) {
  const env = { ...process.env };
  for (const [k, v] of Object.entries(c.env || {})) env[k] = /[\\/]/.test(v) && !/^\d/.test(v) ? abs(v) : v;
  return env;
}

function launch(id, args) {
  const c = COMPONENTS[id];
  const log = fs.openSync(path.join(LOGS, `${id}.log`), 'a');
  const child = spawn(resolveCmd(c.cmd), args || c.args, {
    cwd: abs(c.cwd || '.'), env: envFor(c), detached: true, windowsHide: true, stdio: ['ignore', log, log],
  });
  child.on('error', err => fs.appendFileSync(path.join(LOGS, `${id}.log`), `\n[control] could not start: ${err.message}\n`));
  child.unref();
  fs.closeSync(log);
  return child;
}

async function waitFor(check, timeoutMs) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    await refresh();
    if (check()) return true;
    await sleep(800);
  }
  return false;
}

async function startComponent(id) {
  if (isUp(id)) return;
  const miss = missing(id);
  if (miss.length) throw new Error(`${COMPONENTS[id].name} is not set up on this PC (missing ${miss.join(', ')})`);
  const child = launch(id);
  if (!COMPONENTS[id].finite) spawned.set(id, child.pid);
  const ok = await waitFor(() => isUp(id), id === 'business-ai' ? 240000 : 180000);
  if (!ok) throw new Error(`${COMPONENTS[id].name} did not open port ${portsOf(COMPONENTS[id]).join(', ')}. See control_center/logs/${id}.log`);
}

async function stopComponent(id) {
  const c = COMPONENTS[id];
  if (c.stop) {
    const child = launch(id, c.stop);
    await new Promise(r => child.on('exit', r));
    await waitFor(() => portsOf(c).every(p => !snapshot.ports.has(p)), 30000);
    return;
  }
  for (const port of portsOf(c)) {
    const pid = snapshot.ports.get(port);
    if (!pid) continue;
    const owner = snapshot.procs.get(pid);
    if (!owner || !c.match.test(`${owner.name} ${owner.cmd}`)) {
      throw new Error(`Port ${port} belongs to "${owner?.name || pid}", which is not ${c.name}: left running`);
    }
    await killTree(pid);
  }
  const root = spawned.get(id);
  if (root && snapshot.procs.has(root)) await killTree(root);
  spawned.delete(id);
  await waitFor(() => portsOf(c).every(p => !snapshot.ports.has(p)), 20000);
}

async function releaseShared(m) {
  // Unload this module's models unless another running module needs them; stop the runtime only if this control
  // center started it and nothing running uses it any more (the user's own Ollama app is never stopped).
  for (const runtimeId of m.uses || []) {
    const port = COMPONENTS[runtimeId].port;
    const others = runningModules().filter(o => o.id !== m.id && (o.uses || []).includes(runtimeId));
    const keep = new Set(others.flatMap(o => (o.id === 'chat' ? [chatModel()] : o.models || [])));
    const loaded = snapshot.runtimes[runtimeId]?.loaded.map(l => l.name) || [];
    const toUnload = m.id === 'chat' ? loaded.filter(n => !keep.has(n)) : (m.models || []).filter(n => loaded.includes(n) && !keep.has(n));
    for (const name of toUnload) await unloadModel(port, name);
    if (!others.length && spawned.has(runtimeId)) await stopComponent(runtimeId);
    else if (others.length) notes.set(m.id, `Shared Ollama stays on: ${others.map(o => o.name).join(', ')} uses it.`);
  }
}

async function act(moduleId, action) {
  const m = MODULES.find(x => x.id === moduleId);
  if (!m) throw Object.assign(new Error('unknown module'), { status: 404 });
  if (busy.has(m.id)) throw Object.assign(new Error('already busy'), { status: 409 });
  busy.set(m.id, action === 'start' ? 'starting' : 'stopping');
  notes.delete(m.id);
  (async () => {
    try {
      if (action === 'start') {
        for (const id of m.uses || []) await startComponent(id);
        for (const id of m.components) await startComponent(id);
        notes.set(m.id, `${m.name} is on.`);
      } else {
        for (const id of [...m.components].reverse()) await stopComponent(id);
        await releaseShared(m);
        if (!notes.has(m.id)) notes.set(m.id, `${m.name} is off.`);
      }
    } catch (err) {
      notes.set(m.id, err.message);
    } finally {
      busy.delete(m.id);
      await refresh();
    }
  })();
}

// ------------------------------------------------------------------ HTTP
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
const localOrigin = o => !o || /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(o);

function send(res, status, body, type = 'application/json') {
  res.writeHead(status, { 'content-type': type, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  try {
    if (req.method === 'GET' && url.pathname === '/api/state') return send(res, 200, state());
    const m = url.pathname.match(/^\/api\/modules\/([\w-]+)\/(start|stop)$/);
    if (m) {
      if (req.method !== 'POST') return send(res, 405, { error: 'method_not_allowed' });
      if (req.headers['x-control'] !== '1' || !localOrigin(req.headers.origin)) return send(res, 403, { error: 'forbidden' });
      await act(m[1], m[2]);
      return send(res, 202, { module: m[1], action: m[2] });
    }
    if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, { error: 'method_not_allowed' });
    const rel = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
    const file = path.resolve(PUBLIC, rel);
    if (!file.startsWith(PUBLIC + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return send(res, 404, { error: 'not_found' });
    return send(res, 200, fs.readFileSync(file), TYPES[path.extname(file)] || 'application/octet-stream');
  } catch (err) {
    return send(res, err.status || 500, { error: err.message });
  }
});

await refresh();
setInterval(() => { refresh().catch(() => {}); }, POLL_MS).unref();
server.listen(PORT, '127.0.0.1', () => console.log(`Control center at http://127.0.0.1:${PORT}/ (through the gateway: /_control/)`));
