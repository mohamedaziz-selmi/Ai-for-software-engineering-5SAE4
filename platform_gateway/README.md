# Freelance platform gateway

This standalone addition groups the existing freelance application behind one service boundary and reserves a separate boundary for AI Assistant & Delivery Review. It does not edit, move, merge or reinstall any teammate files.

## Architecture

```text
Browser: http://127.0.0.1:8080
                  |
              API gateway
              /         \
     existing platform   /api/ai/* and /assistant/*
         :8081                    |
     (service adapter)       Your AI service :8003
       /  |  |  |  \        (to be implemented)
   Vite Ollama RAG Sentiment BI
   8766 11434 8000   8001   8002
```

The gateway has exactly two configured upstreams. Only the existing-platform adapter knows the teammates' internal ports. In the report, call this an **existing platform behind a service facade**, alongside the new AI microservice. It is a migration boundary, not a claim that the old code has become one independently packaged process or container.

The facade is a separate process owned by this infrastructure addition. Teammates' existing services continue to run using their normal commands. Their current Vite configuration is unchanged; existing API paths are forwarded by the facade before they reach Vite.

## Run

Requires Node.js 22+. Validated on Node.js 24.19.0 with all nine tests passing. No npm packages or installation step are needed. From this directory, run in two terminals:

```powershell
node run.mjs legacy
```

```powershell
node run.mjs gateway
```

Start the existing frontend and backend processes separately using their existing documented procedure. This package deliberately does not launch or modify them. Open `http://127.0.0.1:8080` to enter through the gateway. Ctrl+C stops each new process.

Defaults work without configuration. To override them, copy `.env.example` to `.env` **inside this directory**, adjust it, and use `npm.cmd run start:legacy` / `npm.cmd run start:gateway`. Never edit the shared root package.json or vite.config.js for this addition. Ports must be unused; startup reports bind errors.

## Routing contract

| Public path | Destination | Path sent upstream |
|---|---|---|
| `/_gateway/health` | Gateway itself | Liveness only; does not assert backend readiness |
| `/api/ai` and `/api/ai/*` | Your service, :8003 | Preserved |
| `/assistant` and `/assistant/*` | Your service, :8003 | Preserved |
| `/ollama/*` | Existing platform -> Ollama | `/ollama` prefix removed |
| `/rag-api/*` | Existing platform -> retrieval | `/rag-api` prefix removed |
| `/sentiment-api/*` | Existing platform -> sentiment | `/sentiment-api` prefix removed |
| `/api/module5/*` | Existing platform -> BI | Preserved |
| All other paths | Existing platform -> Vite | Preserved |

Query strings, methods, bodies, status codes and ordinary headers are forwarded. Requests and responses stream rather than buffering entire uploads or model responses. The proxy never retries requests, so it cannot automatically duplicate a POST. Unreachable upstreams return JSON 502; idle timeouts return 504 before response headers, or close an already-streaming response. WebSocket upgrades support Vite development reload connections. Incoming forwarding headers are removed; they are not trusted identity information.

## Contract for the new AI service

- Bind to loopback port 8003, configurable later.
- Own its CRUD, prompts, local assistant, hosted review and fallback. API keys belong only there.
- Implement `/api/ai/health` honestly, including model/database status.
- Serve its UI and assets under `/assistant/`, with the frontend asset base configured accordingly. Backend API requests use `/api/ai/...` on the same origin.
- Use module-owned storage and environment; do not write to existing Chroma collections or shared Python environments.
- The actual assistant/review implementation is not included in this gateway package. Until it runs, its routes return 502; no mock response is presented as a working AI service.

Visiting `/assistant/` can make the module accessible without editing the old dashboard. Adding a navigation button to the old dashboard remains a task for its owner; the gateway does not inject or rewrite teammates' HTML/JS.

## Scope and validation

This is a **local development/demo gateway**, bound to 127.0.0.1 with local upstreams only. It does not introduce user authentication, authorization, a service registry, TLS, production deployment or a production rate limiter. Existing services remain reachable on their existing ports. Internet-facing deployment requires those decisions separately; a gateway alone does not provide access control.

Run `node --test test/gateway.test.mjs`. The tests use local fake upstreams to verify routing, isolation, prefix preservation, streaming, WebSocket relay and error handling without starting or altering teammates' application. Actual browser integration must be checked with the real services running.

Implementation uses Node's built-in HTTP module: https://nodejs.org/api/http.html. Existing proxy behavior was inspected in the project's vite.config.js; Vite reference: https://vite.dev/config/server-options.html#server-proxy.
