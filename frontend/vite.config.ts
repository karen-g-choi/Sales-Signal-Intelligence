import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const repositoryName = "Sales-Signal-Intelligence";
const isGitHubPagesBuild = process.env.GITHUB_ACTIONS === "true";

export default defineConfig({
  base: isGitHubPagesBuild ? `/${repositoryName}/` : "/",
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
