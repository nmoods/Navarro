import { defineConfig, devices } from "@playwright/test";

// End-to-end tests run the real FastAPI backend + worker in TEST MODE (deterministic stand-in AI providers,
// real render engine and FFmpeg) against the Vite dev server.
// Each run gets a fresh database and storage folder (backend/var is git-ignored).
const run = `./var/e2e/${Date.now()}`;
const backend = process.platform === "win32" ? "..\\backend\\.venv\\Scripts\\python.exe" : "../backend/.venv/bin/python";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 240_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:5174", trace: "retain-on-failure", ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
  webServer: [
    {
      command: `${backend} -m uvicorn app.main:app --host 127.0.0.1 --port 8100`,
      cwd: "../backend",
      url: "http://127.0.0.1:8100/api/v1/health",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        REELFORGE_APP_ENV: "development",
        REELFORGE_DATABASE_URL: `sqlite:///${run}/e2e.db`,
        REELFORGE_STORAGE_ROOT: `${run}/storage`,
        REELFORGE_WORK_ROOT: `${run}/work`,
        REELFORGE_PUBLIC_API_URL: "http://127.0.0.1:8100",
        REELFORGE_CORS_ORIGINS: "http://127.0.0.1:5174",
        REELFORGE_LLM_PROVIDER: "fixture",
        REELFORGE_IMAGE_PROVIDER: "fixture",
        REELFORGE_TTS_PROVIDER: "fixture",
        REELFORGE_STT_PROVIDER: "fixture",
        REELFORGE_RESEARCH_ENABLED: "false",
        REELFORGE_EMBEDDED_WORKER: "true",
        REELFORGE_RATE_LIMIT_PER_MINUTE: "2000",
      },
    },
    {
      command: "npx vite --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_API_URL: "http://127.0.0.1:8100" },
    },
  ],
});
