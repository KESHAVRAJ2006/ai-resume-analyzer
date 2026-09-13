import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The backend allow-lists this exact origin in CORS_ORIGINS, so the port
    // is pinned rather than left to Vite's "next free port" behaviour.
    strictPort: true,
  },
});
