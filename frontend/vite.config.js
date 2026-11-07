import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8010",
      "/health": "http://127.0.0.1:8010",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.js"],
    exclude: ["tests/e2e/**", "node_modules/**"],
  },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("monaco-editor")) return "editor";
          if (id.includes("/mermaid/")) return "mermaid";
        },
      },
    },
  },
});
