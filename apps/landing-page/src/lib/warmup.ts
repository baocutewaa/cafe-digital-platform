import { BACKEND_ORIGIN } from "@/lib/api-client";

let warmedUp = false;

export function warmupBackend(): void {
  if (warmedUp) return;
  warmedUp = true;
  void fetch(`${BACKEND_ORIGIN}/health`, { method: "GET" }).catch(() => {
    // Non-blocking warmup ping
  });
}
