import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  // components rendered in tests (tsconfig keeps JSX for Next)
  oxc: { jsx: { runtime: "automatic" } },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});
