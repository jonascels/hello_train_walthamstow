// Live data from the backend's WebSocket (/ws), with automatic reconnect.
// Shapes mirror backend/app/models.py. Times are ISO-8601 UTC strings.
// (".svelte.ts" lets this file use Svelte's $state outside a component.)

import { serverNow, syncClock } from "./clock";

export type Direction = "up" | "down"; // up = towards London

export type TimingPoint = {
  station_id: string;
  chainage_m: number;
  arr: string | null;
  dep: string | null;
};

export type Train = {
  id: string;
  direction: Direction;
  destination: string;
  prev: TimingPoint; // station before the bridge; dep always set
  next: TimingPoint; // station after the bridge; arr always set
  t_bridge: string; // estimated time at the bridge
};

// A train to draw on the map: every known timing point, in travel order.
export type Vehicle = {
  id: string;
  direction: Direction;
  destination: string;
  calls: TimingPoint[]; // dep always set; arr may be null
};

export type BridgeSnapshot = {
  generated_at: string;
  bridge_id: string;
  bridge_chainage_m: number;
  trains: Train[]; // bridge ETAs for the countdowns, soonest first
  vehicles: Vehicle[]; // everything on the route, for the map
};

export type LiveUpdate = {
  type: "update";
  server_time: string;
  source: string;
  snapshot: BridgeSnapshot | null;
  last_success: string | null;
  last_error: string | null; // set when the latest poll failed
};

export type Connection = "connecting" | "connected" | "disconnected";

const MAX_RETRY_MS = 15_000;
const TICK_MS = 250;
// The server sends an update every poll (~30 s); silence this long means the
// connection is dead even if the browser hasn't noticed.
const STALE_AFTER_MS = 75_000;
const WATCHDOG_CHECK_MS = 5_000;

class Live {
  update = $state<LiveUpdate | null>(null);
  connection = $state<Connection>("connecting");
  /** Server-corrected time (ms), refreshed a few times a second. */
  now = $state(serverNow());

  #socket: WebSocket | null = null;
  #retryMs = 1000;
  #retryTimer: ReturnType<typeof setTimeout> | undefined;
  #lastMessageAt = Date.now();

  start(): () => void {
    this.#connect();
    const tick = setInterval(() => (this.now = serverNow()), TICK_MS);
    const watchdog = setInterval(() => {
      if (this.#isSilent()) this.#reconnectNow();
    }, WATCHDOG_CHECK_MS);
    // After the tablet wakes up, don't wait for the watchdog or the backoff.
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      const open = this.#socket?.readyState === WebSocket.OPEN;
      if (!open || this.#isSilent()) this.#reconnectNow();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearInterval(tick);
      clearInterval(watchdog);
      clearTimeout(this.#retryTimer);
      document.removeEventListener("visibilitychange", onVisible);
      const socket = this.#socket;
      this.#socket = null; // stops reconnecting
      socket?.close();
    };
  }

  /** Open but silent for too long (the server sends every ~30 s)? */
  #isSilent(): boolean {
    const open = this.#socket?.readyState === WebSocket.OPEN;
    return open && Date.now() - this.#lastMessageAt > STALE_AFTER_MS;
  }

  /**
   * Drop the current socket and connect straight away. A sleeping tablet can
   * leave a socket that looks open but is dead and never fires `close`.
   */
  #reconnectNow(): void {
    if (this.#socket?.readyState === WebSocket.CONNECTING) return; // already trying
    clearTimeout(this.#retryTimer);
    const old = this.#socket;
    this.#socket = null; // so its onclose doesn't schedule another retry
    old?.close();
    this.#retryMs = 1000;
    this.#connect();
  }

  #connect(): void {
    this.connection = "connecting";
    // Same host as the page; in dev Vite proxies /ws to the backend.
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${proto}://${location.host}/ws`);
    this.#socket = socket;
    this.#lastMessageAt = Date.now(); // give the new socket a fair chance

    socket.onopen = () => {
      this.connection = "connected";
      this.#retryMs = 1000;
    };
    socket.onmessage = (event) => {
      const update = JSON.parse(event.data) as LiveUpdate;
      syncClock(update.server_time);
      this.update = update;
      this.#lastMessageAt = Date.now();
    };
    socket.onclose = () => {
      if (this.#socket !== socket) return; // replaced or stopped on purpose
      this.connection = "disconnected";
      // Retry with backoff: 1 s, 2 s, 4 s … up to 15 s.
      this.#retryTimer = setTimeout(() => this.#connect(), this.#retryMs);
      this.#retryMs = Math.min(this.#retryMs * 2, MAX_RETRY_MS);
    };
  }
}

export const live = new Live();
