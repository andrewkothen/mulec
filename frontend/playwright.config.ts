import { defineConfig } from "@playwright/test";
const port = process.env.MULEC_TEST_PORT === "3000" ? 3000 : 8765;
const baseURL = `http://127.0.0.1:${port}`;
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180000,
  use: {
    actionTimeout: 15000,
    baseURL,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: `.venv/bin/python -m uvicorn backend.api.app:create_app --factory --host 127.0.0.1 --port ${port}`,
    cwd: "..",
    url: `${baseURL}/api/health`,
    reuseExistingServer: !process.env.CI && port === 8765,
    timeout: 30000,
    env: {
      MULEC_DATA_DIR: "tmp/browser-data",
      MULEC_MODELS_DIR: "tmp/browser-models",
    },
  },
});
