import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// In dev, the browser talks only to Vite (:5173); Vite forwards /api and /ws
// to the FastAPI backend (:8000), so there are no CORS issues.
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
