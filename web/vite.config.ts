import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Static SPA; relative base so the build can be served from any sub-path.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5174, host: true },
});
