/**
 * Live event stream via WebSocket.
 *
 * Falls back to REST polling when the backend WebSocket endpoint is not
 * available (which is the case in the default deployment — the backend
 * exposes a polling endpoint instead of a full WS for simplicity).
 */
import { api } from "./api";

export type LiveListener = (events: any[]) => void;

export class LiveEventStream {
  private timer: number | null = null;
  private lastSeen: string | null = null;
  private stopped = false;

  constructor(private intervalMs = 3000) {}

  start(onEvents: LiveListener) {
    this.stopped = false;
    const tick = async () => {
      if (this.stopped) return;
      try {
        const res = await api.listEvents({ size: 30, page: 1 });
        const items = res.items;
        let fresh = items;
        if (this.lastSeen) {
          const idx = items.findIndex((e) => e.event_id === this.lastSeen);
          fresh = idx === -1 ? items : items.slice(0, idx);
        }
        if (items.length > 0) this.lastSeen = items[0].event_id;
        if (fresh.length > 0) onEvents(fresh);
      } catch {
        /* swallow — polling is best-effort */
      }
    };
    tick();
    this.timer = window.setInterval(tick, this.intervalMs);
  }

  stop() {
    this.stopped = true;
    if (this.timer !== null) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }
}