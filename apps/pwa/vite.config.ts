/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Cohort Coach",
        short_name: "Cohort Coach",
        display: "standalone",
        start_url: "/",
        background_color: "#ffffff",
        theme_color: "#1f6f5c",
        icons: [{ src: "icon.svg", sizes: "any", type: "image/svg+xml" }],
      },
    }),
  ],
  server: { proxy: { "/api": "http://localhost:8000" } },
  test: { environment: "node" },
});
