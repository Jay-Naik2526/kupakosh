import { defineConfig } from "@playwright/test";

// Smoke test against a running site: `make web` (dev, :3000) + `make api`, or the single-origin share build on :8010
// (KK_URL=http://localhost:8010 npx playwright test).
export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: { baseURL: process.env.KK_URL ?? "http://localhost:3000", viewport: { width: 1440, height: 900 } },
  reporter: [["list"]],
});
