import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    fs: {
      strict: false,
      allow: [root],
    },
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
