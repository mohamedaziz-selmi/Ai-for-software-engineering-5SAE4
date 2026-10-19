// Control center bubble: a draggable "chat head" on every page served by the group gateway. It opens into the live
// architecture map and one on/off switch per module. Rendered in a Shadow DOM, so it neither affects the page under it
// nor is affected by it. Plain JavaScript, no dependencies. Owner's microservice (control_center, :8090).
(() => {
  if (window.__cerebroControl) return;
  window.__cerebroControl = true;
  const script = document.currentScript;
  const BASE = script?.dataset.controlBase ?? '';
  const PAGE = script?.dataset.mode === 'page';
  const reduce = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* not remembered */ } },
  };

  // One font for the widget, declared on the page (font faces are not read inside a shadow root).
  const font = document.createElement('style');
  font.textContent = `@font-face{font-family:"CC Grotesk";src:url("${BASE}/fonts/hanken-grotesk-latin-wght-normal.woff2") format("woff2");font-weight:100 900;font-display:swap}`;
  document.head.append(font);

  const CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; }
  .cc { --bg: oklch(0.19 0.012 255 / 0.9); --bg-solid: oklch(0.19 0.012 255); --raise: oklch(0.25 0.013 255 / 0.85);
    --line: oklch(1 0 0 / 0.1); --line-2: oklch(1 0 0 / 0.18); --text: oklch(0.96 0.004 255); --text-2: oklch(0.8 0.01 255);
    --text-3: oklch(0.66 0.012 255); --on: oklch(0.89 0.19 127); --on-ink: oklch(0.2 0.045 130); --warn: oklch(0.84 0.14 80);
    --fail: oklch(0.72 0.16 25); --off: oklch(0.52 0.012 255); --spring: cubic-bezier(0.2, 0.9, 0.3, 1.2);
    --ease: cubic-bezier(0.23, 1, 0.32, 1);
    font-family: "CC Grotesk", "Segoe UI", system-ui, sans-serif; color: var(--text); font-size: 14px; line-height: 1.45;
    -webkit-font-smoothing: antialiased; }
  button { font: inherit; color: inherit; }
  :focus-visible { outline: 2px solid var(--on); outline-offset: 2px; }

  /* The chat head */
  .head { position: fixed; z-index: 2147483000; top: 0; left: 0; width: 58px; height: 58px; padding: 0; border: 0; border-radius: 50%;
    background: var(--bg-solid); box-shadow: 0 10px 30px -8px oklch(0 0 0 / 0.55), inset 0 1px 0 oklch(1 0 0 / 0.12), 0 0 0 1px var(--line);
    cursor: grab; touch-action: none; transition: transform 460ms var(--spring), box-shadow 200ms var(--ease); }
  .head.dragging { cursor: grabbing; transition: none; }
  .head:hover { box-shadow: 0 14px 36px -8px oklch(0 0 0 / 0.6), inset 0 1px 0 oklch(1 0 0 / 0.16), 0 0 0 1px var(--line-2); }
  .head svg { position: absolute; inset: 0; width: 100%; height: 100%; }
  .head .ring-track { stroke: oklch(1 0 0 / 0.1); }
  .head .ring { stroke: var(--ring, var(--on)); stroke-linecap: round; transition: stroke-dashoffset 600ms var(--ease), stroke 300ms; }
  .head .glyph { transition: transform 320ms var(--spring); transform-origin: 29px 29px; }
  .head[aria-expanded="true"] .glyph { transform: rotate(45deg) scale(0.86); }
  .badge { position: absolute; top: -4px; right: -6px; min-width: 22px; height: 20px; padding: 0 6px; border-radius: 10px;
    background: var(--on); color: var(--on-ink); font-size: 11px; font-weight: 700; line-height: 20px; text-align: center;
    box-shadow: 0 0 0 2px var(--bg-solid); font-variant-numeric: tabular-nums; }
  .press { transform: scale(0.94) !important; }

  /* The panel */
  .panel { position: fixed; z-index: 2147483001; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; width: min(780px, calc(100vw - 24px));
    height: min(640px, calc(100vh - 24px)); border-radius: 18px; background: var(--bg); color: var(--text);
    -webkit-backdrop-filter: blur(20px) saturate(140%); backdrop-filter: blur(20px) saturate(140%);
    box-shadow: 0 30px 80px -20px oklch(0 0 0 / 0.65), inset 0 1px 0 oklch(1 0 0 / 0.1), 0 0 0 1px var(--line); overflow: hidden;
    opacity: 0; transform: scale(0.6); pointer-events: none; visibility: hidden;
    transition: opacity 180ms var(--ease), transform 200ms var(--ease), visibility 0s linear 200ms; }
  .panel.open { opacity: 1; transform: scale(1); pointer-events: auto; visibility: visible; transition: opacity 220ms var(--ease), transform 460ms var(--spring), visibility 0s; }
  .page .panel { position: relative; inset: auto; width: 100%; height: 100vh; border-radius: 0; opacity: 1; transform: none; pointer-events: auto; box-shadow: none; }
  @media (prefers-reduced-transparency: reduce) { .panel { background: var(--bg-solid); -webkit-backdrop-filter: none; backdrop-filter: none; } }

  header { display: grid; grid-template-columns: 1fr auto; gap: 10px 16px; align-items: center; padding: 16px 18px 14px; border-bottom: 1px solid var(--line); }
  h2 { margin: 0; font-size: 17px; font-weight: 700; letter-spacing: -0.01em; }
  header p { margin: 2px 0 0; color: var(--text-3); font-size: 12.5px; }
  .meters { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
  .meter { display: grid; gap: 5px; padding: 8px 10px; border-radius: 10px; background: var(--raise); box-shadow: inset 0 0 0 1px var(--line); }
  .meter span { color: var(--text-3); font-size: 11.5px; }
  .meter b { font-size: 15px; font-weight: 650; font-variant-numeric: tabular-nums; }
  .meter i { display: block; height: 3px; border-radius: 2px; background: var(--fill, var(--on)); width: var(--w, 0%); transition: width 600ms var(--ease); }
  .meter.hot b { color: var(--fail); } .meter.warm b { color: var(--warn); }
  .x { width: 32px; height: 32px; border: 0; border-radius: 9px; background: none; color: var(--text-2); cursor: pointer; font-size: 20px; line-height: 1; }
  .x:hover { background: var(--raise); color: var(--text); }
  .page .x { display: none; }

  .body { display: grid; grid-template-columns: 340px minmax(0, 1fr); min-height: 0; }
  .map { padding: 12px 6px 12px 14px; border-right: 1px solid var(--line); overflow: auto; }
  .map h3, .list h3 { margin: 4px 4px 8px; color: var(--text-3); font-size: 12px; font-weight: 600; }
  .map svg { display: block; width: 100%; height: auto; }
  .node rect { fill: var(--raise); stroke: var(--line-2); transition: stroke 300ms, fill 300ms; }
  .node.on rect { stroke: oklch(0.89 0.19 127 / 0.65); }
  .node.partial rect, .node.starting rect, .node.stopping rect { stroke: var(--warn); }
  .node.not_set_up rect { stroke-dasharray: 3 3; fill: transparent; }
  .node.hl rect { fill: oklch(0.89 0.19 127 / 0.14); }
  .node text { fill: var(--text); font-size: 10.5px; font-weight: 600; }
  .node text.port { fill: var(--text-3); font-size: 9px; font-weight: 500; font-variant-numeric: tabular-nums; }
  .node .dot { fill: var(--off); transition: fill 300ms; }
  .node.on .dot { fill: var(--on); } .node.partial .dot, .node.starting .dot, .node.stopping .dot { fill: var(--warn); }
  .edge { fill: none; stroke: oklch(1 0 0 / 0.14); stroke-width: 1.2; transition: stroke 300ms; }
  .edge.live { stroke: oklch(0.89 0.19 127 / 0.75); stroke-dasharray: 3 5; animation: flow 1.1s linear infinite; }
  @keyframes flow { to { stroke-dashoffset: -16; } }
  .node { cursor: pointer; }

  .list { padding: 12px 14px; overflow: auto; }
  .row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px 12px; padding: 11px 12px; margin-bottom: 6px; border-radius: 12px;
    background: var(--raise); box-shadow: inset 0 0 0 1px var(--line); transition: box-shadow 250ms var(--ease), background-color 250ms var(--ease); }
  .row.flash { box-shadow: inset 0 0 0 1px var(--on); }
  .row strong { font-size: 14px; font-weight: 650; }
  .row .role { color: var(--text-3); font-size: 12px; }
  .row .meta { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
  .chip { display: inline-flex; align-items: center; gap: 5px; height: 21px; padding: 0 8px; border-radius: 6px; background: oklch(1 0 0 / 0.06);
    color: var(--text-2); font-size: 11.5px; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .chip.model.loaded { color: var(--on); } .chip.model.missing { color: var(--warn); }
  .chip.yours { background: oklch(0.89 0.19 127 / 0.16); color: var(--on); font-weight: 600; }
  .status { font-size: 12px; font-weight: 600; color: var(--text-3); }
  .status.on { color: var(--on); } .status.partial, .status.starting, .status.stopping { color: var(--warn); } .status.not_set_up { color: var(--text-3); }
  .note { grid-column: 1 / -1; margin: 0; color: var(--text-2); font-size: 12px; }
  .note.err { color: var(--fail); }
  .side { display: grid; justify-items: end; gap: 6px; align-content: start; }
  .open-link { color: var(--text-2); font-size: 12px; text-decoration: none; }
  .open-link:hover { color: var(--on); }
  .switch { position: relative; width: 44px; height: 26px; padding: 0; border: 0; border-radius: 13px; background: oklch(1 0 0 / 0.14); cursor: pointer;
    transition: background-color 220ms var(--ease); }
  .switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: var(--text);
    box-shadow: 0 2px 6px oklch(0 0 0 / 0.35); transition: transform 320ms var(--spring); }
  .switch[aria-checked="true"] { background: var(--on); }
  .switch[aria-checked="true"]::after { transform: translateX(18px); background: var(--on-ink); }
  .switch:disabled { cursor: not-allowed; opacity: 0.45; }
  .switch.busy::after { animation: breathe 900ms ease-in-out infinite alternate; }
  @keyframes breathe { to { transform: translateX(9px) scale(0.8); } }
  .confirm { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 9px;
    background: oklch(0.72 0.16 25 / 0.12); color: var(--text); font-size: 12.5px; }
  .confirm button { height: 26px; padding: 0 10px; border: 0; border-radius: 7px; background: var(--fail); color: oklch(0.15 0.02 25); font-weight: 650; cursor: pointer; }
  .confirm button.keep { background: oklch(1 0 0 / 0.12); color: var(--text); }

  footer { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 10px 18px; border-top: 1px solid var(--line); color: var(--text-3); font-size: 12px; }
  footer a { color: var(--text-2); text-decoration: none; } footer a:hover { color: var(--on); }
  footer .spacer { flex: 1; }
  .legend { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
  .empty { padding: 30px; color: var(--text-3); text-align: center; }

  @media (max-width: 720px) {
    .panel { width: calc(100vw - 16px); height: calc(100vh - 16px); }
    .body { grid-template-columns: minmax(0, 1fr); overflow: auto; }
    .map { border-right: 0; border-bottom: 1px solid var(--line); overflow: visible; }
    .list { overflow: visible; }
    .meters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition-duration: 1ms !important; }
  }`;

  // ----------------------------------------------------------------- architecture map layout (viewBox 330 x 420)
  const N = { w: 108, h: 30 };
  const NODES = [
    { id: 'browser', label: 'Browser', port: 'you', x: 8, y: 8, w: 82 },
    { id: 'gateway', label: 'Gateway', port: ':8080', x: 8, y: 196, w: 82, module: 'platform' },
    { id: 'platform', label: 'Dashboard', port: ':8081 :8766', x: 116, y: 8, module: 'platform' },
    { id: 'rag', label: 'RAG', port: ':8000', x: 132, y: 50, w: 92, module: 'rag' },
    { id: 'sentiment', label: 'Sentiment', port: ':8001', x: 132, y: 88, w: 92, module: 'sentiment' },
    { id: 'bi', label: 'BI', port: ':8002', x: 132, y: 126, w: 92, module: 'bi' },
    { id: 'assistant', label: 'Assistant', port: ':8003', x: 116, y: 182, module: 'assistant' },
    { id: 'advisor', label: 'Advisor', port: ':8004', x: 116, y: 230, module: 'advisor' },
    { id: 'marketplace', label: 'Marketplace', port: ':8005', x: 116, y: 278, module: 'marketplace' },
    { id: 'business', label: 'Business AI', port: ':8900-8905', x: 116, y: 326, module: 'business' },
    { id: 'chat', label: 'AI chat', port: 'dashboard', x: 116, y: 374, module: 'chat' },
    { id: 'ollama', label: 'Ollama shared', port: ':11434', x: 240, y: 300, w: 86, runtime: 11434 },
    { id: 'ollama2', label: 'Ollama', port: ':11435', x: 240, y: 182, w: 86, runtime: 11435 },
    { id: 'ollama3', label: 'Ollama CPU', port: ':11436', x: 240, y: 252, w: 86, runtime: 11436 },
  ];
  const EDGES = [
    ['browser', 'gateway', 'v'], ['gateway', 'platform'], ['gateway', 'assistant'], ['gateway', 'advisor'], ['gateway', 'marketplace'],
    ['gateway', 'business'], ['platform', 'rag', 'tree'], ['platform', 'sentiment', 'tree'], ['platform', 'bi', 'tree'], ['platform', 'chat', 'tree'],
    ['assistant', 'ollama2'], ['marketplace', 'ollama3'], ['advisor', 'ollama'], ['business', 'ollama'], ['chat', 'ollama'],
  ];
  const nodeById = Object.fromEntries(NODES.map(n => [n.id, { w: N.w, h: N.h, ...n }]));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function edgePath(a, b, kind) {
    const A = nodeById[a], B = nodeById[b];
    if (kind === 'v') return `M${A.x + A.w / 2} ${A.y + A.h} V${B.y}`;
    if (kind === 'tree') { const x = A.x + 8; return `M${x} ${A.y + A.h} V${B.y + B.h / 2} H${B.x}`; }
    const x1 = A.x + A.w, y1 = A.y + A.h / 2, x2 = B.x, y2 = B.y + B.h / 2, mx = (x1 + x2) / 2;
    return `M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`;
  }

  // ----------------------------------------------------------------- DOM
  const host = document.createElement('cerebro-control');
  const root = host.attachShadow({ mode: 'open' });
  root.innerHTML = `<style>${CSS}</style>
    <div class="cc ${PAGE ? 'page' : ''}">
      ${PAGE ? '' : `<button class="head" type="button" aria-expanded="false" aria-controls="cc-panel" aria-label="Open the control center">
        <svg viewBox="0 0 58 58" aria-hidden="true">
          <circle class="ring-track" cx="29" cy="29" r="26" fill="none" stroke-width="3"/>
          <circle class="ring" cx="29" cy="29" r="26" fill="none" stroke-width="3" transform="rotate(-90 29 29)" stroke-dasharray="163.4" stroke-dashoffset="163.4"/>
          <g class="glyph" fill="none" stroke="oklch(0.89 0.19 127)" stroke-width="2" stroke-linecap="round">
            <path d="M22 34 L29 23 L36 34 Z" stroke-opacity="0.55"/>
            <circle cx="29" cy="22" r="3.4" fill="oklch(0.89 0.19 127)"/><circle cx="21.5" cy="35" r="3.4" fill="oklch(0.89 0.19 127)"/><circle cx="36.5" cy="35" r="3.4" fill="oklch(0.89 0.19 127)"/>
          </g>
        </svg><span class="badge" hidden></span></button>`}
      <section class="panel" id="cc-panel" role="dialog" aria-label="Control center" ${PAGE ? '' : 'aria-modal="false"'}>
        <header>
          <div><h2>Control center</h2><p>Cerebro platform: every module, its ports and its model. One switch each.</p></div>
          <button class="x" type="button" aria-label="Close the control center">&times;</button>
          <div class="meters"></div>
        </header>
        <div class="body"><div class="map"><h3>Architecture</h3><div class="svg"></div></div><div class="list"><h3>Modules</h3><div class="rows"><p class="empty">Reading the platform…</p></div></div></div>
        <footer><span class="legend"><i style="--c: oklch(0.89 0.19 127)"></i>On</span><span class="legend"><i style="--c: oklch(0.84 0.14 80)"></i>Starting or partial</span>
          <span class="legend"><i style="--c: oklch(0.52 0.012 255)"></i>Off</span><span class="spacer"></span><span class="updated"></span>
          ${PAGE ? '' : '<a href="http://127.0.0.1:8090/" target="_blank" rel="noopener">Open full page</a>'}</footer>
      </section>
    </div>`;
  (document.body || document.documentElement).append(host);
  const $ = sel => root.querySelector(sel);
  const head = $('.head'), panel = $('.panel');

  // ----------------------------------------------------------------- dragging, snapping, opening
  const SIZE = 58, MARGIN = 16;
  let pos = store.get('cerebro.control.pos') || { side: 'right', y: window.innerHeight - SIZE - 96 };
  let open = PAGE;
  const clampY = y => Math.max(MARGIN, Math.min(window.innerHeight - SIZE - MARGIN, y));
  const xFor = side => (side === 'left' ? MARGIN : window.innerWidth - SIZE - MARGIN);
  function place() {
    if (!head) return;
    pos.y = clampY(pos.y);
    head.style.transform = `translate3d(${xFor(pos.side)}px, ${pos.y}px, 0)`;
    placePanel();
  }
  function placePanel() {
    if (PAGE || !head) return;
    const w = panel.offsetWidth || 780, h = panel.offsetHeight || 640;
    const left = pos.side === 'right' ? window.innerWidth - SIZE - MARGIN * 2 - w : SIZE + MARGIN * 2;
    const top = Math.max(12, Math.min(window.innerHeight - h - 12, pos.y + SIZE / 2 - h / 2));
    panel.style.left = `${Math.max(12, left)}px`;
    panel.style.top = `${top}px`;
    const originX = pos.side === 'right' ? '100%' : '0%';
    panel.style.transformOrigin = `${originX} ${pos.y + SIZE / 2 - top}px`;
  }
  function setOpen(next) {
    open = next;
    head?.setAttribute('aria-expanded', String(open));
    panel.classList.toggle('open', open);
    if (open) { placePanel(); poll(true); setTimeout(() => $('.x')?.focus({ preventScroll: true }), 50); }
    else head?.focus({ preventScroll: true });
    schedule();
  }
  if (head) {
    let drag = null;
    head.addEventListener('pointerdown', e => {
      drag = { x0: e.clientX, y0: e.clientY, sx: xFor(pos.side), sy: pos.y, moved: false };
      head.setPointerCapture(e.pointerId);
      head.classList.add('press');
    });
    head.addEventListener('pointermove', e => {
      if (!drag) return;
      const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
      if (!drag.moved && Math.hypot(dx, dy) < 5) return;
      drag.moved = true;
      head.classList.add('dragging');
      head.classList.remove('press');
      head.style.transform = `translate3d(${drag.sx + dx}px, ${drag.sy + dy}px, 0)`;
    });
    const end = e => {
      if (!drag) return;
      head.classList.remove('dragging', 'press');
      if (drag.moved) {
        const x = drag.sx + (e.clientX - drag.x0);
        pos = { side: x + SIZE / 2 < window.innerWidth / 2 ? 'left' : 'right', y: clampY(drag.sy + (e.clientY - drag.y0)) };
        store.set('cerebro.control.pos', pos);
        place();
      } else setOpen(!open);
      drag = null;
    };
    head.addEventListener('pointerup', end);
    head.addEventListener('pointercancel', () => { drag = null; head.classList.remove('dragging', 'press'); place(); });
    head.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(!open); } });
    window.addEventListener('resize', place);
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && open) setOpen(false); });
    document.addEventListener('pointerdown', e => { if (open && !e.composedPath().includes(host)) setOpen(false); });
    $('.x').addEventListener('click', () => setOpen(false));
    place();
  }

  // ----------------------------------------------------------------- data
  let state = null;
  const confirming = new Set();
  async function call(path, method = 'GET') {
    const r = await fetch(`${BASE}${path}`, { method, headers: method === 'POST' ? { 'X-Control': '1' } : {}, cache: 'no-store' });
    if (!r.ok && r.status !== 202) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    return r.json();
  }
  let timer = null;
  function schedule() { clearTimeout(timer); timer = setTimeout(() => poll(), open ? 2000 : 6000); }
  async function poll(now) {
    if (now) clearTimeout(timer);
    try { state = await call('/api/state'); render(); } catch { renderOffline(); }
    schedule();
  }

  function mb(n) { return n >= 1024 ? `${(n / 1024).toFixed(1)} GB` : `${n} MB`; }
  function meters(s) {
    const g = s.gpu;
    const t = g?.temp;
    const cell = (label, value, pct, cls = '') => `<div class="meter ${cls}"><span>${label}</span><b>${value}</b><i style="--w:${Math.min(100, pct || 0)}%"></i></div>`;
    return cell('CPU', s.cpu === null ? '...' : `${s.cpu}%`, s.cpu)
      + cell('RAM', `${s.ram}%`, s.ram, s.ram >= 85 ? 'warm' : '')
      + cell('GPU temperature', g ? `${t} °C` : 'n/a', g ? (t / 90) * 100 : 0, t >= 76 ? 'hot' : t >= 68 ? 'warm' : '')
      + cell('GPU memory', g ? `${mb(g.vramUsedMb)} of ${mb(g.vramTotalMb)}` : 'n/a', g ? (100 * g.vramUsedMb) / g.vramTotalMb : 0);
  }

  function nodeStatus(n) {
    if (n.id === 'browser') return 'on';
    if (n.runtime) return state.runtimes.find(r => r.port === n.runtime)?.up ? 'on' : 'off';
    return state.modules.find(m => m.id === n.module)?.status || 'off';
  }
  function mapSvg() {
    const st = Object.fromEntries(NODES.map(n => [n.id, nodeStatus(n)]));
    const edges = EDGES.map(([a, b, k]) => `<path class="edge ${st[a] === 'on' && st[b] === 'on' ? 'live' : ''}" d="${edgePath(a, b, k)}"/>`).join('');
    const nodes = NODES.map(n0 => {
      const n = nodeById[n0.id];
      return `<g class="node ${st[n.id]}" data-module="${n.module || ''}" transform="translate(${n.x} ${n.y})">
        <title>${esc(n.label)} ${esc(n.port)}: ${st[n.id].replace('_', ' ')}</title>
        <rect width="${n.w}" height="${n.h}" rx="8"/><circle class="dot" cx="11" cy="${n.h / 2}" r="3.5"/>
        <text x="21" y="13">${esc(n.label)}</text><text class="port" x="21" y="24">${esc(n.port)}</text></g>`;
    }).join('');
    return `<svg viewBox="0 0 330 412" role="img" aria-label="Architecture map with live status">${edges}${nodes}</svg>`;
  }

  const STATUS = { on: 'On', off: 'Off', partial: 'Partly on', starting: 'Starting…', stopping: 'Stopping…', not_set_up: 'Not set up' };
  function row(m) {
    const on = m.status === 'on' || m.status === 'partial';
    const busy = m.status === 'starting' || m.status === 'stopping';
    const ports = [...m.components.flatMap(c => c.ports), ...m.uses.flatMap(u => u.ports)];
    const usage = m.ramMb ? `<span class="chip">RAM ${mb(m.ramMb)}</span>` : '';
    const vram = m.vramMb ? `<span class="chip">GPU ${mb(m.vramMb)}</span>` : '';
    const models = m.models.map(x => `<span class="chip model ${x.loaded ? 'loaded' : x.installed === false ? 'missing' : ''}" title="${x.loaded ? 'Loaded in memory' : x.installed === false ? 'Not installed in Ollama :' + x.runtime : 'Installed, not loaded'}">${esc(x.name)}${x.installed === false ? ' (not installed)' : ''}</span>`).join('');
    const note = m.notSetUp.length && m.status === 'not_set_up'
      ? `<p class="note">Not set up on this PC: ${esc(m.notSetUp.join(', '))}. See the module's INTEGRATION.md.</p>`
      : m.note ? `<p class="note ${/not |did not|belongs|could not|unknown/i.test(m.note) && !/ is (on|off)\./.test(m.note) ? 'err' : ''}">${esc(m.note)}</p>` : '';
    const ask = confirming.has(m.id) ? `<div class="confirm" role="group" aria-label="Confirm stopping ${esc(m.name)}">
        <span>This stops the gateway and the dashboard, so this page stops answering. Start them again from <b>http://127.0.0.1:8090/</b>.</span>
        <button type="button" data-confirm="${m.id}">Stop it</button><button type="button" class="keep" data-keep="${m.id}">Keep on</button></div>` : '';
    return `<div class="row" data-row="${m.id}">
      <div><strong>${esc(m.name)}</strong> ${m.owner ? '<span class="chip yours">Yours</span>' : ''}<div class="role">${esc(m.role)}</div></div>
      <div class="side"><button class="switch ${busy ? 'busy' : ''}" type="button" role="switch" aria-checked="${on}" data-toggle="${m.id}"
        aria-label="${on ? 'Turn off' : 'Turn on'} ${esc(m.name)}" ${busy || m.status === 'not_set_up' ? 'disabled' : ''}></button>
        <span class="status ${m.status}">${STATUS[m.status] || m.status}</span></div>
      <div class="meta">${ports.map(p => `<span class="chip">:${p}</span>`).join('')}${usage}${vram}${models}
        ${m.url && m.status === 'on' ? `<a class="open-link" href="${m.url}">Open</a>` : ''}</div>
      ${note}${ask}</div>`;
  }

  function render() {
    $('.meters').innerHTML = meters(state.system);
    $('.svg').innerHTML = mapSvg();
    $('.rows').innerHTML = state.modules.map(row).join('');
    $('.updated').textContent = `Updated ${new Date(state.at).toLocaleTimeString()}`;
    const onCount = state.modules.filter(m => m.status === 'on').length;
    if (head) {
      const t = state.system.gpu?.temp;
      head.style.setProperty('--ring', t >= 76 ? 'oklch(0.72 0.16 25)' : t >= 68 ? 'oklch(0.84 0.14 80)' : 'oklch(0.89 0.19 127)');
      $('.ring').setAttribute('stroke-dashoffset', String(163.4 * (1 - onCount / state.modules.length)));
      const badge = $('.badge');
      badge.hidden = false;
      badge.textContent = `${onCount}/${state.modules.length}`;
      head.setAttribute('aria-label', `Open the control center: ${onCount} of ${state.modules.length} modules on${t ? `, GPU ${t} °C` : ''}`);
    }
  }
  function renderOffline() {
    $('.rows').innerHTML = '<p class="empty">The control center is not answering. Start it with control_center\\START_PLATFORM.cmd.</p>';
    $('.svg').innerHTML = '';
  }

  root.addEventListener('click', async e => {
    const t = e.target.closest('[data-toggle],[data-confirm],[data-keep],.node');
    if (!t) return;
    if (t.matches('.node')) {
      const id = t.dataset.module;
      const r = root.querySelector(`[data-row="${id}"]`);
      if (r) { r.scrollIntoView({ block: 'nearest', behavior: reduce() ? 'auto' : 'smooth' }); r.classList.add('flash'); setTimeout(() => r.classList.remove('flash'), 900); }
      return;
    }
    if (t.dataset.keep) { confirming.delete(t.dataset.keep); return render(); }
    const id = t.dataset.toggle || t.dataset.confirm;
    const m = state?.modules.find(x => x.id === id);
    if (!m) return;
    const turningOff = m.status === 'on' || m.status === 'partial';
    // Stopping the platform from a page it serves takes this page down: ask first.
    if (turningOff && id === 'platform' && !PAGE && !t.dataset.confirm) { confirming.add(id); return render(); }
    confirming.delete(id);
    try { await call(`/api/modules/${id}/${turningOff ? 'stop' : 'start'}`, 'POST'); } catch (err) { m.note = err.message; }
    poll(true);
  });
  root.addEventListener('mouseover', e => {
    const r = e.target.closest('[data-row]');
    root.querySelectorAll('.node').forEach(n => n.classList.toggle('hl', Boolean(r) && n.dataset.module === r.dataset.row));
  });

  if (PAGE) panel.classList.add('open');
  poll(true);
})();
