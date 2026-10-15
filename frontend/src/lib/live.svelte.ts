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

class Live {
  update = $state<LiveUpdate | null>(null);
  connection = $state<Connection>("connecting");
  /** Server-corrected time (ms), refreshed a few times a second. */
  now = $state(serverNow());

  #socket: WebSocket | null = null;
  #retryMs = 1000;

  start(): () => void {
    this.#connect();
    const tick = setInterval(() => (this.now = serverNow()), TICK_MS);
    return () => {
      clearInterval(tick);
      this.#socket?.close();
      this.#socket = null; // stops reconnecting
    };
  }

  #connect(): void {
    this.connection = "connecting";
    // Same host as the page; in dev Vite proxies /ws to the backend.
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${proto}://${location.host}/ws`);
    this.#socket = socket;

    socket.onopen = () => {
      this.connection = "connected";
      this.#retryMs = 1000;
    };
    socket.onmessage = (event) => {
      const update = JSON.parse(event.data) as LiveUpdate;
      syncClock(update.server_time);
      this.update = update;
    };
    socket.onclose = () => {
      if (this.#socket !== socket) return; // closed on purpose by stop()
      this.connection = "disconnected";
      // Retry with backoff: 1 s, 2 s, 4 s … up to 15 s.
      setTimeout(() => this.#connect(), this.#retryMs);
      this.#retryMs = Math.min(this.#retryMs * 2, MAX_RETRY_MS);
    };
  }
}

export const live = new Live();
