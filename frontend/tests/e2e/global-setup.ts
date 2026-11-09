import { rmSync } from "node:fs";
import path from "node:path";

// Fresh database and storage for every e2e run.
export default function globalSetup() {
  rmSync(path.resolve(import.meta.dirname, "../../../backend/var/e2e"), { recursive: true, force: true });
}
