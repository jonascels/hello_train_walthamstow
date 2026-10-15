// Keeps the tablet's screen on while the board is visible (Screen Wake Lock
// API). Browsers release the lock whenever the page is hidden, so we ask
// again each time it becomes visible.
//
// Needs a secure context: works on https:// or http://localhost, but NOT on
// plain http:// over the local network. There, set the tablet's own
// "auto-lock"/"screen timeout" to never instead.

export type WakeLockStatus = "active" | "unsupported" | "insecure" | "failed" | "off";

class ScreenWake {
  status = $state<WakeLockStatus>("off");
  #lock: WakeLockSentinel | null = null;

  start(): () => void {
    if (!window.isSecureContext) {
      this.status = "insecure";
      return () => {};
    }
    if (!("wakeLock" in navigator)) {
      this.status = "unsupported";
      return () => {};
    }
    const onVisible = () => {
      if (document.visibilityState === "visible") this.#request();
    };
    document.addEventListener("visibilitychange", onVisible);
    this.#request();
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      this.#lock?.release();
    };
  }

  async #request(): Promise<void> {
    try {
      this.#lock = await navigator.wakeLock.request("screen");
      this.status = "active";
      this.#lock.addEventListener("release", () => (this.status = "off"));
    } catch {
      // e.g. battery saver on, or the page isn't visible yet.
      this.status = "failed";
    }
  }
}

export const screenWake = new ScreenWake();
