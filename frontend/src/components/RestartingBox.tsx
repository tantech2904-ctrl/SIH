import { useEffect, useRef, useState } from "react";
import { Loader2, RefreshCw, AlertCircle } from "lucide-react";

const POLL_INTERVAL_MS = 2000;
const HARD_TIMEOUT_MS = 120_000;

type Phase = "restarting" | "still" | "slow" | "timeout" | "ready";

export function RestartingBox({ onReady }: { onReady: () => void }) {
  const [phase, setPhase] = useState<Phase>("restarting");
  const startedAt = useRef<number>(Date.now());
  const stopped = useRef(false);
  const wentDown = useRef(false);

  useEffect(() => {
    stopped.current = false;
    startedAt.current = Date.now();
    wentDown.current = false;

    async function poll() {
      if (stopped.current) return;
      const elapsed = Date.now() - startedAt.current;

      if (elapsed > HARD_TIMEOUT_MS) {
        setPhase("timeout");
        return;
      }

      try {
        const r = await fetch("/api/v1/health", { cache: "no-store" });
        if (r.ok) {
          if (wentDown.current) {
            // Backend was down, now it's back up. Ready.
            setPhase("ready");
            return;
          }
          // Backend up, but hasn't gone down yet. Keep waiting.
        } else {
          // Non-2xx response (502, 503, etc.) → backend is not reachable.
          wentDown.current = true;
        }
      } catch {
        // Network error → backend is not reachable.
        wentDown.current = true;
      }

      if (elapsed < 30_000) setPhase("restarting");
      else if (elapsed < 60_000) setPhase("still");
      else setPhase("slow");

      window.setTimeout(poll, POLL_INTERVAL_MS);
    }

    poll();
    return () => {
      stopped.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="panel p-6 w-full max-w-sm text-center space-y-3">
      {phase !== "ready" && phase !== "timeout" && (
        <Loader2 className="w-8 h-8 mx-auto text-soc-accent animate-spin" />
      )}
      {phase === "timeout" && (
        <AlertCircle className="w-8 h-8 mx-auto text-red-400" />
      )}
      {phase === "ready" && (
        <RefreshCw className="w-8 h-8 mx-auto text-emerald-400" />
      )}

      {phase === "restarting" && (
        <div className="text-sm">Backend restarting…</div>
      )}
      {phase === "still" && (
        <div className="text-sm">Still restarting, please wait…</div>
      )}
      {phase === "slow" && (
        <div className="text-sm">Taking longer than expected. Please hold on…</div>
      )}
      {phase === "timeout" && (
        <div className="text-sm text-red-400">
          Backend did not come back after 2 minutes.
          <div className="text-2xs text-soc-textDim mt-1">
            Check the container logs:{" "}
            <span className="font-mono">docker compose logs backend</span>
          </div>
        </div>
      )}
      {phase === "ready" && (
        <>
          <div className="text-sm text-emerald-400">
            Server restarted. Continue to login.
          </div>
          <button
            className="btn btn-primary text-xs w-full justify-center"
            onClick={onReady}
          >
            Continue
          </button>
        </>
      )}
    </div>
  );
}