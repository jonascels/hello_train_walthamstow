import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    svelte(),
    // Makes the app installable ("Add to Home Screen") and caches it so it
    // reloads even if the Wi-Fi blips. Icons come from pwa-assets.config.ts.
    VitePWA({
      registerType: "autoUpdate", // a wall-mounted tablet picks up new versions by itself
      manifest: {
        name: "Hello Train!",
        short_name: "Hello Train",
        description: "Live countdown to trains over the West Ave bridge",
        theme_color: "#823a62",
        background_color: "#15191e",
        display: "standalone",
        display_override: ["fullscreen", "standalone"],
        orientation: "any",
        icons: [
          { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "maskable-icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024, // MapLibre is ~1 MB
        // Live data must always come from the server, never the cache.
        navigateFallbackDenylist: [/^\/api/, /^\/ws/],
        runtimeCaching: [
          {
            // Base map tiles, styles and fonts: show cached ones instantly.
            urlPattern: /^https:\/\/tiles\.openfreemap\.org\//,
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "map-tiles",
              expiration: { maxEntries: 3000, maxAgeSeconds: 30 * 24 * 3600 },
            },
          },
        ],
      },
    }),
  ],
  // In dev, the browser talks only to Vite (:5173); Vite forwards /api and /ws
  // to the FastAPI backend (:8000), so there are no CORS issues.
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
