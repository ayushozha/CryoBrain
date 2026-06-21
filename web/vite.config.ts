import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages project site uses /CryoBrain/; local dev defaults to relative "./".
export default defineConfig({
  base: process.env.VITE_BASE ?? "./",
  plugins: [react()],
  server: { port: 5174, host: true },
});
