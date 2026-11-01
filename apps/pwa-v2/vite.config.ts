/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// The app shell and every screen are precached, so the teacher screens (T1 to T3) work with no
// signal after the first load. Only the Practice Class (P06) needs a live connection.
const api = `http://localhost:${process.env["API_PORT"] ?? "8000"}`;

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg"],
      manifest: {
        id: "/",
        name: "Cohort Coach",
        short_name: "Cohort Coach",
        description: "Know what your class gets wrong, then fix it.",
        lang: "en",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        scope: "/",
        background_color: "#f7fafa", // --paper in src/styles/tokens.css
        theme_color: "#0b6b6b", // --pen in src/styles/tokens.css
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
          { src: "icon.svg", sizes: "any", type: "image/svg+xml" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,json,webmanifest}"],
        navigateFallback: "index.html",
        // The API is never cached: the Practice Class needs the live service, the rest is local.
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  server: { proxy: { "/api": api } },
  preview: { proxy: { "/api": api } },
  test: { environment: "node", exclude: ["e2e/**", "node_modules/**"] },
});
