# Control center

A small local microservice (Node.js, no dependencies) that shows the Cerebro platform's architecture live and turns
each module on or off, together with the model it needs. It appears as a round button on every page served by the
group gateway (http://127.0.0.1:8080), and as a full page at http://127.0.0.1:8090/.

## Run everything

| Goal | Do this |
|---|---|
| Start the front end (control center, gateway, facade, dashboard) and open the browser | Double-click `control_center\START_PLATFORM.cmd` |
| Same, plus modules | `powershell -ExecutionPolicy Bypass -File control_center\start_platform.ps1 -With assistant,business` |
| Turn any module on or off | The round button, bottom right of any page; or http://127.0.0.1:8090/ |
| Stop everything | Double-click `control_center\STOP_PLATFORM.cmd` |

Module ids for `-With`: `platform`, `chat`, `rag`, `sentiment`, `bi`, `assistant`, `advisor`, `marketplace`, `business`.

## What one switch does

| Module | Turns on | Model |
|---|---|---|
| Cerebro platform | Gateway :8080, facade :8081, dashboard :8766 | none |
| Cerebro AI chat | Shared Ollama :11434 | Dashboard rule: `llama3.2:3b` if installed, else the first listed |
| RAG service, Sentiment, BI | :8000, :8001, :8002 | none (own embedding models) |
| AI Assistant & Delivery Review | Private Ollama :11435 + API :8003 | `qwen2.5:7b-instruct` (or RAFT, chosen in the module) |
| Freelance Advisor | API :8004 + shared Ollama | `qwen3:4b-instruct` |
| Freelance Marketplace AI | Budget API :8005 + CPU Ollama :11436 | `qwen2.5:0.5b` |
| Cerebro Business AI | Its 6 servers :8900 to :8905 + shared Ollama | `gemma3:4b` |

- A shared Ollama stops only when no running module uses it. Its models are unloaded when their module stops, so GPU
  memory is freed; the Ollama app you started yourself is never stopped.
- A module that is not set up on this PC (missing Python environment) shows **Not set up** and its switch is disabled.
- The button's ring shows how many modules are on; it turns amber at 68 °C and red at 76 °C (GPU limit: 79 °C).

## Safety

- Listens on 127.0.0.1 only. Turning things on or off needs a POST with the `X-Control` header from a local page.
- A process is stopped only if it owns the module's port **and** its command line matches the expected program
  (`registry.mjs`), so an unrelated app on the same port is left alone.
- Stopping the platform from a page it serves asks first, because that page goes down with it.

## Files

| File | Role |
|---|---|
| `server.mjs` | HTTP API (:8090), background probes every 3 s, start/stop logic |
| `registry.mjs` | Every component (port, command, folder) and every module (switch) |
| `system.mjs` | Read-only probes: ports (netstat), processes, CPU, RAM, GPU (nvidia-smi), Ollama |
| `public/bubble.js` | The button and panel (Shadow DOM, plain JavaScript) |
| `start_platform.ps1`, `stop_platform.ps1` | The run and stop scripts (and their `.cmd` shortcuts) |
| `logs/` | One log per started component (not in Git) |

The gateway adds the button to HTML pages (`platform_gateway/proxy.mjs`, `CONTROL_BUBBLE=0` turns it off) and
forwards `/_control/...` here.

## Troubleshooting

| Symptom | Cause, fix |
|---|---|
| No round button | The page was not opened through :8080, or the control center is off: run `START_PLATFORM.cmd` |
| A module stays "Starting…" then shows an error | Read `control_center\logs\<component>.log` |
| "Port … belongs to …, left running" | Another program uses that port; close it, then switch again |
| Cerebro Business AI refuses work | Its resource guard stops at 80% RAM or CPU: close other apps |
