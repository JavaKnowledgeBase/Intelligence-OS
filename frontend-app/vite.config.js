import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite development config for the React frontend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
  },
});
