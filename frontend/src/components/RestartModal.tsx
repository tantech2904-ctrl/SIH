import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

interface Props {
  open: boolean;
  restartKeys: string[];
  saving: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

const COUNTDOWN_SECONDS = 3;

export function RestartModal({
  open, restartKeys, saving, error, onCancel, onConfirm,
}: Props) {
  const [remaining, setRemaining] = useState(COUNTDOWN_SECONDS);

  useEffect(() => {
    if (!open) {
      setRemaining(COUNTDOWN_SECONDS);
      return;
    }
    setRemaining(COUNTDOWN_SECONDS);
    const iv = window.setInterval(() => {
      setRemaining((r) => (r > 0 ? r - 1 : 0));
    }, 1000);
    return () => window.clearInterval(iv);
  }, [open]);

  if (!open) return null;

  const ready = remaining === 0 && !saving;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="panel w-full max-w-lg p-5 space-y-3">
        <div className="flex items-center gap-2 text-amber-400">
          <AlertTriangle className="w-5 h-5" />
          <div className="text-base font-semibold">Backend restart required</div>
        </div>

        <div className="text-sm text-soc-textMuted">
          The following settings require a backend restart to take effect:
        </div>

        <ul className="text-xs font-mono text-soc-accent list-disc list-inside space-y-0.5">
          {restartKeys.map((k) => <li key={k}>{k}</li>)}
        </ul>

        <div className="text-xs text-soc-textDim">
          The backend will be briefly unavailable (2–5 seconds).
          Any in-flight requests will fail. UDP datagrams received during
          the restart window are dropped.
        </div>

        {error && (
          <div className="text-xs text-red-400">{error}</div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            className="btn text-xs"
            onClick={onCancel}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            className="btn btn-primary text-xs"
            onClick={onConfirm}
            disabled={!ready}
          >
            {saving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Saving…
              </>
            ) : remaining > 0 ? (
              <>Confirm in {remaining}…</>
            ) : (
              "Confirm & restart"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}