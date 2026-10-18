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

export default defineConfig({
	publicDir: "cerebro/_next/static/media",
	server: {
		host: "0.0.0.0",
		port: 8766,
		strictPort: true,
		proxy: {
			"/ollama": ollamaProxy,
			"/rag-api": ragProxy,
			"/sentiment-api": sentimentProxy,
			"/api/module5": module5Proxy,
			"/api/ai": assistantProxy,
			"/assistant": assistantProxy,
		},
	},
	preview: {
		proxy: {
			"/ollama": ollamaProxy,
			"/rag-api": ragProxy,
			"/sentiment-api": sentimentProxy,
			"/api/module5": module5Proxy,
			"/api/ai": assistantProxy,
			"/assistant": assistantProxy,
		},
	},
});
