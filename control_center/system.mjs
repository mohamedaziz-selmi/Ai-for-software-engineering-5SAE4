// Read-only probes of this Windows PC: listening ports, processes, CPU, RAM, GPU and Ollama runtimes.
// Nothing here changes the system. Each probe fails soft: a missing tool gives an empty or null value, never a crash.
import { execFile } from 'node:child_process';
import os from 'node:os';

function run(file, args, timeout = 8000) {
  return new Promise(resolve => {
    execFile(file, args, { timeout, windowsHide: true, maxBuffer: 32 * 1024 * 1024 }, (error, stdout) => resolve(error ? '' : stdout));
  });
}

// Port -> owning PID, from `netstat -ano` (fast, no PowerShell).
export async function listeningPorts() {
  const out = await run('netstat.exe', ['-ano', '-p', 'TCP']);
  const ports = new Map();
  for (const line of out.split(/\r?\n/)) {
    const m = line.match(/^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)/i);
    if (m && !ports.has(Number(m[2]))) ports.set(Number(m[2]), Number(m[3]));
  }
  return ports;
}

// All processes with parent, command line, memory and CPU time (one CIM query).
export async function processes() {
  const script = 'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,WorkingSetSize,KernelModeTime,UserModeTime | ConvertTo-Json -Compress';
  const out = await run('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script], 15000);
  const map = new Map();
  try {
    for (const p of JSON.parse(out || '[]')) {
      map.set(p.ProcessId, {
        pid: p.ProcessId, ppid: p.ParentProcessId, name: p.Name, cmd: p.CommandLine || '',
        rss: Number(p.WorkingSetSize || 0), cpuTime: (Number(p.KernelModeTime || 0) + Number(p.UserModeTime || 0)) / 1e7,
      });
    }
  } catch { /* leave empty */ }
  return map;
}

export function descendants(procs, pid) {
  const children = new Map();
  for (const p of procs.values()) {
    if (!children.has(p.ppid)) children.set(p.ppid, []);
    children.get(p.ppid).push(p.pid);
  }
  const out = [];
  const stack = [pid];
  while (stack.length) {
    const current = stack.pop();
    if (out.includes(current) || !procs.has(current)) continue;
    out.push(current);
    stack.push(...(children.get(current) || []));
  }
  return out;
}

let lastCpu = null;
export function systemLoad() {
  const cpus = os.cpus();
  const total = cpus.reduce((a, c) => a + Object.values(c.times).reduce((x, y) => x + y, 0), 0);
  const idle = cpus.reduce((a, c) => a + c.times.idle, 0);
  let cpu = null;
  if (lastCpu) cpu = Math.max(0, Math.min(100, 100 * (1 - (idle - lastCpu.idle) / Math.max(1, total - lastCpu.total))));
  lastCpu = { total, idle };
  return { cpu, ram: 100 * (1 - os.freemem() / os.totalmem()), ramTotalGb: os.totalmem() / 2 ** 30, cores: cpus.length };
}

export async function gpu() {
  const out = await run('nvidia-smi', ['--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits']);
  const parts = out.trim().split(/\r?\n/)[0]?.split(',').map(s => s.trim());
  if (!parts || parts.length < 5) return null;
  return { name: parts[0], temp: Number(parts[1]), util: Number(parts[2]), vramUsed: Number(parts[3]), vramTotal: Number(parts[4]) };
}

// Models loaded in an Ollama runtime, and the ones installed there.
export async function ollama(port) {
  const get = async path => {
    try {
      const r = await fetch(`http://127.0.0.1:${port}${path}`, { signal: AbortSignal.timeout(2500) });
      return r.ok ? r.json() : null;
    } catch { return null; }
  };
  const [ps, tags] = await Promise.all([get('/api/ps'), get('/api/tags')]);
  if (!ps && !tags) return null;
  return {
    loaded: (ps?.models || []).map(m => ({ name: m.name, vramMb: Math.round((m.size_vram || 0) / 2 ** 20), sizeMb: Math.round((m.size || 0) / 2 ** 20) })),
    installed: (tags?.models || []).map(m => m.name),
  };
}

export async function unloadModel(port, model) {
  try {
    await fetch(`http://127.0.0.1:${port}/api/generate`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model, keep_alive: 0 }),
      signal: AbortSignal.timeout(15000),
    });
  } catch { /* already gone */ }
}

export function killTree(pid) {
  return run('taskkill.exe', ['/PID', String(pid), '/T', '/F']);
}
