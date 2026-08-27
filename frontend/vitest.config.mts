import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// tsconfig.json sets `jsx: "preserve"` for Next.js's own SWC pipeline, so Vite's
// built-in esbuild transform won't touch JSX. This plugin handles it for tests.
export default defineConfig({
  plugins: [react()],
});
