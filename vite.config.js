import { defineConfig } from "vite";

const ollamaProxy = {
	target: "http://127.0.0.1:11434",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/ollama/, ""),
};

const ragProxy = {
	target: "http://127.0.0.1:8000",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/rag-api/, ""),
};

const sentimentProxy = {
	target: "http://127.0.0.1:8001",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/sentiment-api/, ""),
};

const module5Proxy = {
	target: "http://127.0.0.1:8002",
	changeOrigin: true,
};

const assistantProxy = {
	target: "http://127.0.0.1:8003",
	changeOrigin: true,
};

// The research API (agentic-freelance-advisor, FastAPI) on its own port 8004 (8000 is the retrieval service).
// A run takes minutes and streams progress events, so the proxy must not time out or buffer: no timeout is set,
// and the API sends a keep-alive line every 15 seconds.
const advisorProxy = {
	target: "http://127.0.0.1:8004",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/advisor/, ""),
};

// Freelance Marketplace AI (marketplace_ml, FastAPI) on its own port 8005. Only its three endpoints are proxied,
// so /api/ai and /api/module5 keep reaching their own services.
const marketplaceProxy = {
	target: "http://127.0.0.1:8005",
	changeOrigin: true,
};

// Freelance Marketplace AI matcher: Qwen2.5 0.5B on its own CPU-only Ollama, port 11436. The author used 11435,
// which is module_assistant_delivery's private Ollama here. Listed before /ollama so it is matched first.
const ollamaMatchProxy = {
	target: "http://127.0.0.1:11436",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/ollama-match/, ""),
};

// Cerebro Business AI (cerebro_business_ai, its own microservice): screens on :8905 and API gateway on :8900, under
// /business-ai and /business-ai-api like the group gateway. /business-ai-api is listed first: Vite matches prefixes.
const businessAiApiProxy = {
	target: "http://127.0.0.1:8900",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/business-ai-api/, ""),
};

const businessAiUiProxy = {
	target: "http://127.0.0.1:8905",
	changeOrigin: true,
	rewrite: (path) => path.replace(/^\/business-ai/, ""),
};

export default defineConfig({
	publicDir: "cerebro/_next/static/media",
	server: {
		host: "0.0.0.0",
		port: 8766,
		strictPort: true,
		proxy: {
			"/ollama-match": ollamaMatchProxy,
			"/ollama": ollamaProxy,
			"/rag-api": ragProxy,
			"/sentiment-api": sentimentProxy,
			"/api/module5": module5Proxy,
			"/api/ai": assistantProxy,
			"/assistant": assistantProxy,
			"/advisor": advisorProxy,
			"/business-ai-api": businessAiApiProxy,
			"/business-ai": businessAiUiProxy,
			"/api/health": marketplaceProxy,
			"/api/match": marketplaceProxy,
			"/api/budget": marketplaceProxy,
		},
	},
	preview: {
		proxy: {
			"/ollama-match": ollamaMatchProxy,
			"/ollama": ollamaProxy,
			"/rag-api": ragProxy,
			"/sentiment-api": sentimentProxy,
			"/api/module5": module5Proxy,
			"/api/ai": assistantProxy,
			"/assistant": assistantProxy,
			"/advisor": advisorProxy,
			"/business-ai-api": businessAiApiProxy,
			"/business-ai": businessAiUiProxy,
			"/api/health": marketplaceProxy,
			"/api/match": marketplaceProxy,
			"/api/budget": marketplaceProxy,
		},
	},
});
