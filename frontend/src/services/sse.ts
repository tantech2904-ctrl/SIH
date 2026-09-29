/**
 * SSE client — fetch + ReadableStream reader.
 *
 * Why not EventSource?
 *   EventSource does not support custom headers, so we cannot send the
 *   Authorization: Bearer header that the backend requires. A fetch-based
 *   reader keeps the existing auth model intact.
 *
 * Contract: start() opens the stream; stop() closes it. On unexpected
 * disconnect, we retry with exponential backoff (1s → 30s cap). On 401, we
 * stop and let the AuthContext's refresh-then-logout flow take over.
 *
 * Replay policy:
 *   Last-Event-ID is sent only on a reconnect that happens *after* a
 *   successful connection within the same client instance. The very first
 *   connection of a client never asks for replay, so a page mount always
 *   starts clean. reset() clears the anchor and disables replay for the
 *   next connect — use it when the caller clears the visible list so old
 *   events don't come back.
 */
import { getAccessToken } from "./api";

export type SSEEventHandler = (payload: any) => void;
export type SSEStatus = "connecting" | "connected" | "reconnecting";
export type SSEStatusHandler = (s: SSEStatus) => void;

export class EventStreamClient {
  private controller: AbortController | null = null;
  private stopped = false;
  private lastEventId: string | null = null;
  private retryDelayMs = 1000;
  private readonly maxDelayMs = 30000;
  // When true, the next connect() will send Last-Event-ID. Set to false
  // for the first connection and for user-initiated restarts (pause/resume,
  // clear), so we never re-request history we've already shown.
  private allowReplay = false;

  constructor(
    private url: string,
    private onEvent: SSEEventHandler,
    private onStatus?: SSEStatusHandler,
  ) {}

  start() {
    this.stopped = false;
    // First connection of this client instance: no replay.
    this.allowReplay = false;
    this.onStatus?.("connecting");
    void this.connect();
  }

  stop() {
    this.stopped = true;
    if (this.controller) {
      this.controller.abort();
      this.controller = null;
    }
  }

  /**
   * Forget the last event id. The next connect() will not request replay.
   * Use this when the caller clears the visible list, so old events don't
   * come back on the next reconnect.
   */
  reset() {
    this.lastEventId = null;
    this.allowReplay = false;
  }

  private async connect() {
    if (this.stopped) return;

    const token = getAccessToken();
    if (!token) return;

    this.controller = new AbortController();

    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    };
    // Only ask for replay when we're recovering from a drop mid-session.
    if (this.allowReplay && this.lastEventId) {
      headers["Last-Event-ID"] = this.lastEventId;
    }

    try {
      const res = await fetch(this.url, {
        headers,
        signal: this.controller.signal,
      });

      if (res.status === 401) {
        return;
      }
      if (!res.ok || !res.body) {
        throw new Error(`SSE HTTP ${res.status}`);
      }

      this.retryDelayMs = 1000;
      this.onStatus?.("connected");
      // After a successful connect, subsequent reconnects may request replay.
      this.allowReplay = true;

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!this.stopped) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx: number;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const raw = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          this.handleFrame(raw);
        }
      }
    } catch {
      if (this.stopped) return;
    }

    if (!this.stopped) {
      this.onStatus?.("reconnecting");
      setTimeout(() => void this.connect(), this.retryDelayMs);
      this.retryDelayMs = Math.min(this.retryDelayMs * 2, this.maxDelayMs);
    }
  }

  private handleFrame(raw: string) {
    let id: string | null = null;
    let data: string | null = null;
    for (const line of raw.split("\n")) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("id:")) id = line.slice(3).trim();
      else if (line.startsWith("data:")) {
        const chunk = line.slice(5).trim();
        data = data === null ? chunk : data + "\n" + chunk;
      }
    }
    if (id) this.lastEventId = id;
    if (data) {
      try {
        const parsed = JSON.parse(data);
        this.onEvent(parsed);
      } catch {
        /* ignore malformed payloads */
      }
    }
  }
}