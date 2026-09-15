import { Loader2 } from "lucide-react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-8 text-soc-textMuted gap-2">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorBox({ error }: { error: any }) {
  const msg = error?.message || String(error);
  return (
    <div className="panel border-red-500/40 bg-red-500/5 p-3 text-sm text-red-300">
      <div className="font-semibold mb-1">Request failed</div>
      <div className="font-mono text-xs">{msg}</div>
      {error?.correlationId ? (
        <div className="text-2xs text-soc-textDim mt-1">
          correlation_id: {error.correlationId}
        </div>
      ) : null}
    </div>
  );
}

export function EmptyState({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-soc-textDim gap-1">
      <span className="text-sm">{message}</span>
      {hint ? <span className="text-2xs">{hint}</span> : null}
    </div>
  );
}