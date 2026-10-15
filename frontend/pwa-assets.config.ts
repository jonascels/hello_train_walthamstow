// Generates the PWA / home-screen icons from public/icon.svg.
// Re-run after changing the icon:  npx pwa-assets-generator
import { defineConfig, minimal2023Preset } from "@vite-pwa/assets-generator/config";

export default defineConfig({
  preset: {
    ...minimal2023Preset,
    // Fill the padding around maskable/Apple icons with the tile colour.
    maskable: { ...minimal2023Preset.maskable, resizeOptions: { background: "#823a62" } },
    apple: { ...minimal2023Preset.apple, resizeOptions: { background: "#823a62" } },
  },
  images: ["public/icon.svg"],
});
