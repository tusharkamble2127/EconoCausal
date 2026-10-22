import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Volume II Chapter 1.10: local deployment -- Vite dev server on 5173,
// FastAPI backend on 8000 (see src/api/client.js for the base URL).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
