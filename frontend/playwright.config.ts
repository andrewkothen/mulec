import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180000,
  use: {
    actionTimeout: 15000,
    baseURL: "http://127.0.0.1:8765",
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      ".venv/bin/python -m uvicorn backend.api.app:create_app --factory --host 127.0.0.1 --port 8765",
    cwd: "..",
    url: "http://127.0.0.1:8765/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
    env: { MULEC_DATA_DIR: "tmp/browser-data" },
  },
});
