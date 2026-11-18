import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Calls to /api/... go to the TS API, so the browser only talks to one address (no CORS).
    proxy: {
      "/api": "http://localhost:3000",
    },
  },
});
