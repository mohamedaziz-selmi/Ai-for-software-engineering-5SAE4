// What the control center can start and stop. Paths are relative to the application root (the folder above this one).
// A component is one listening process; a module is what one switch controls (its components plus the model it needs).
// `match` must fit the command line of the process that owns the port before anything is stopped, so the control
// center never stops an unrelated program that happens to use the same port.

const py = (venv) => `${venv}/Scripts/python.exe`;
const uvicorn = (app, port, extra = []) => ['-m', 'uvicorn', app, '--host', '127.0.0.1', '--port', String(port), ...extra];

export const COMPONENTS = {
  gateway: { name: 'Group gateway', port: 8080, cwd: 'platform_gateway', cmd: 'node', args: ['run.mjs', 'gateway'], match: /run\.mjs["']?\s+gateway/i },
  facade: { name: 'Platform facade', port: 8081, cwd: 'platform_gateway', cmd: 'node', args: ['run.mjs', 'legacy'], match: /run\.mjs["']?\s+legacy/i },
  dashboard: { name: 'Dashboard (Vite)', port: 8766, cwd: '.', cmd: 'cmd.exe', args: ['/d', '/c', 'npm.cmd run dev'], match: /vite|npm/i, requires: ['node_modules'] },
  'shared-ollama': { name: 'Shared Ollama', port: 11434, cmd: 'ollama', args: ['serve'], match: /ollama/i, runtime: true },
  rag: { name: 'RAG service', port: 8000, cwd: 'rag_service', cmd: py('rag_service/.venv'), args: uvicorn('api:app', 8000), match: /uvicorn/i, requires: [py('rag_service/.venv')] },
  sentiment: { name: 'Sentiment classifier', port: 8001, cwd: 'sentiment classifier', cmd: py('rag_service/.venv'), args: uvicorn('api:app', 8001), match: /uvicorn/i, requires: [py('rag_service/.venv')] },
  bi: { name: 'Business Intelligence', port: 8002, cwd: 'module5_business_intelligence', cmd: py('rag_service/.venv'), args: uvicorn('api:app', 8002), match: /uvicorn/i, requires: [py('rag_service/.venv')] },
  'assistant-ollama': {
    name: 'Assistant Ollama', port: 11435, cmd: 'powershell.exe',
    args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'module_assistant_delivery/scripts/start_ollama.ps1'],
    match: /ollama/i, runtime: true, requires: ['module_assistant_delivery/scripts/start_ollama.ps1'],
  },
  'assistant-api': {
    name: 'Assistant API', port: 8003, cwd: 'module_assistant_delivery/backend', cmd: py('module_assistant_delivery/.venv'), args: uvicorn('api:app', 8003),
    env: { HF_HOME: 'module_assistant_delivery/storage/hf' }, match: /uvicorn/i, requires: [py('module_assistant_delivery/.venv')],
  },
  advisor: { name: 'Advisor API', port: 8004, cwd: 'agentic-freelance-advisor', cmd: py('agentic-freelance-advisor/.venv'), args: uvicorn('app.main:app', 8004), match: /uvicorn/i, requires: [py('agentic-freelance-advisor/.venv')] },
  'marketplace-api': {
    name: 'Budget API', port: 8005, cwd: 'marketplace_ml/project matching/src', cmd: py('marketplace_ml/.venv'), args: uvicorn('ai_api:app', 8005),
    match: /uvicorn/i, requires: [py('marketplace_ml/.venv')],
  },
  'matcher-ollama': {
    name: 'Matcher Ollama (CPU)', port: 11436, cmd: 'ollama', args: ['serve'], match: /ollama/i, runtime: true,
    env: { OLLAMA_HOST: '127.0.0.1:11436', OLLAMA_MODELS: 'marketplace_ml/.ollama-models', OLLAMA_LLM_LIBRARY: 'cpu', OLLAMA_NUM_PARALLEL: '1' },
  },
  'business-ai': {
    name: 'Business AI (6 servers)', port: 8900, ports: [8900, 8901, 8902, 8903, 8904, 8905], cwd: 'cerebro_business_ai', cmd: 'powershell.exe',
    args: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'portable/cerebro.ps1', '-Action', 'Start', '-NoBrowser'],
    stop: ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'portable/cerebro.ps1', '-Action', 'Stop'],
    match: /python|uvicorn|serve_frontend/i, requires: ['cerebro_business_ai/.runtime/setup-complete.json'], finite: true,
  },
};

// One switch per module (owner's choice). `uses` lists shared runtimes started with the module and stopped only when
// no running module still uses them; `models` are unloaded from a shared runtime when the module stops.
export const MODULES = [
  { id: 'platform', name: 'Cerebro platform', role: 'Gateway, facade and dashboard: the front end of the project', components: ['gateway', 'facade', 'dashboard'], url: 'http://127.0.0.1:8080/' },
  { id: 'chat', name: 'Cerebro AI chat', role: 'Dashboard chat, on the shared Ollama (its model follows the dashboard rule)', components: [], uses: ['shared-ollama'] },
  { id: 'rag', name: 'RAG service', role: 'Document search for the platform', components: ['rag'] },
  { id: 'sentiment', name: 'Sentiment classifier', role: 'Review sentiment', components: ['sentiment'] },
  { id: 'bi', name: 'Business Intelligence', role: 'Sales forecasting dashboards', components: ['bi'] },
  { id: 'assistant', name: 'AI Assistant & Delivery Review', role: 'Grounded answers and delivery review', components: ['assistant-ollama', 'assistant-api'], url: 'http://127.0.0.1:8080/assistant/', owner: true },
  { id: 'advisor', name: 'Freelance Advisor', role: 'Research agent', components: ['advisor'], uses: ['shared-ollama'], models: ['qwen3:4b-instruct'] },
  { id: 'marketplace', name: 'Freelance Marketplace AI', role: 'Matching and budget prediction', components: ['marketplace-api', 'matcher-ollama'] },
  { id: 'business', name: 'Cerebro Business AI', role: 'Hiring, sales, job checks, listings', components: ['business-ai'], uses: ['shared-ollama'], models: ['gemma3:4b'], url: 'http://127.0.0.1:8080/business-ai/' },
];

export const RUNTIMES = [
  { id: 'shared-ollama', port: 11434 },
  { id: 'assistant-ollama', port: 11435 },
  { id: 'matcher-ollama', port: 11436 },
];
