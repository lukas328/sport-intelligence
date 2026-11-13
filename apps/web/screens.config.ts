import { defineConfig, devices } from "@playwright/test";

/** Screenshots of every screen for docs/screens (see docs/screens/README.md); not part of the e2e run. */
export default defineConfig({
  testDir: "./screens",
  globalSetup: "./e2e/global-setup.ts",
  timeout: 1_800_000,
  reporter: "list",
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", reducedMotion: "reduce", trace: "off", locale: "de-CH" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
