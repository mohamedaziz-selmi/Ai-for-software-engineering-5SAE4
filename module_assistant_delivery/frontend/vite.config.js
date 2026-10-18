import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built into dist/ and served by the module backend under /assistant/ (the gateway routes it to :8003).
// `npm run dev` (port 8767) proxies API calls to the backend for UI work.
export default defineConfig({
	base: "/assistant/",
	plugins: [react()],
	build: { outDir: "dist", emptyOutDir: true },
	server: {
		host: "127.0.0.1",
		port: 8767,
		strictPort: true,
		proxy: { "/api/ai": { target: "http://127.0.0.1:8003", changeOrigin: true } },
	},
});
