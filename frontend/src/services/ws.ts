/**
 * Live event stream.
 *
 * Implementation: REST polling with a fixed interval.
 *
 * Design notes:
 *  - `lastSeen` is owned by the CALLER, not the poller. This lets the
 *    caller preserve it across Pause/Resume cycles so that resuming does
 *    not re-emit the last N events.
 *  - Polling is paused while the browser tab is hidden. Background-tab
 *    timer throttling (Chrome/Edge) slows setInterval to ~1 tick/minute
 *    for hidden tabs, so keeping the interval running adds nothing.
 *  - On visibility change back to "visible", an immediate tick fires so
 *    the UI catches up without waiting for the next interval.
 *
 * The class is deliberately small and dependency-free. If a WebSocket
 * endpoint is added later, this class can be replaced behind the same
 * `start(onEvents)` / `stop()` contract.
 */
import { api } from "./api";

export type LiveListener = (events: any[]) => void;

export interface LiveStreamOptions {
  /** Read/write access to the last seen event_id. Persist across instances. */
  lastSeenRef: { current: string | null };
}

export class LiveEventStream {
  private timer: number | null = null;
  private stopped = false;
  private onEvents: LiveListener | null = null;
  private visibilityBound = false;

  private readonly onVisibilityChange = () => {
    if (this.stopped) return;
    if (document.visibilityState === "visible") {
      this.restartTimer();
      // Immediate catch-up poll when the tab becomes visible again.
      void this.tick();
    } else {
      this.clearTimer();
    }
  };

  constructor(
    private intervalMs = 3000,
    private opts: LiveStreamOptions,
  ) {}

  start(onEvents: LiveListener) {
    this.onEvents = onEvents;
    this.stopped = false;

    if (!this.visibilityBound) {
      document.addEventListener("visibilitychange", this.onVisibilityChange);
      this.visibilityBound = true;
    }

    // If we start while hidden (e.g. the user navigated here in a hidden
    // tab), don't spin the interval until they actually look at the page.
    if (document.visibilityState !== "hidden") {
      void this.tick();
      this.restartTimer();
    }
  }

  stop() {
    this.stopped = true;
    this.clearTimer();
    if (this.visibilityBound) {
      document.removeEventListener("visibilitychange", this.onVisibilityChange);
      this.visibilityBound = false;
    }
    this.onEvents = null;
  }

  private restartTimer() {
    this.clearTimer();
    if (this.stopped) return;
    this.timer = window.setInterval(() => void this.tick(), this.intervalMs);
  }

  private clearTimer() {
    if (this.timer !== null) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }

  private async tick() {
    if (this.stopped) return;
    try {
      const res = await api.listEvents({ size: 30, page: 1 });
      const items = res.items;
      if (items.length === 0) return;

      const lastSeen = this.opts.lastSeenRef.current;
      let fresh = items;
      if (lastSeen) {
        const idx = items.findIndex((e) => e.event_id === lastSeen);
        fresh = idx === -1 ? items : items.slice(0, idx);
      }
      this.opts.lastSeenRef.current = items[0].event_id;
      if (fresh.length > 0 && this.onEvents) {
        this.onEvents(fresh);
      }
    } catch {
      /* swallow — polling is best-effort */
    }
  }
}