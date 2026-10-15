<script lang="ts">
  // Connection state, data freshness, screen wake lock and attribution.
  import { formatTime } from "../lib/clock";
  import type { Connection, LiveUpdate } from "../lib/live.svelte";
  import type { WakeLockStatus } from "../lib/wakeLock.svelte";

  let {
    update,
    connection,
    wake,
  }: { update: LiveUpdate | null; connection: Connection; wake: WakeLockStatus } =
    $props();

  const lastSuccess = $derived(
    update?.last_success ? formatTime(Date.parse(update.last_success), true) : null,
  );
  const wakeNote = $derived(
    {
      active: "",
      off: "",
      unsupported: "Screen may sleep (browser can't keep it on)",
      insecure: "Screen may sleep (needs https)",
      failed: "Screen may sleep",
    }[wake],
  );
</script>

<footer class="status">
  <span class="dot {connection}" title={connection}></span>
  {#if connection !== "connected"}
    <!-- Countdowns keep running on the last data while we reconnect. -->
    <span class="warn">{update ? "Reconnecting…" : "Connecting…"}</span>
  {:else if update?.last_error}
    <span class="warn">{update.source} unavailable, showing data from {lastSuccess ?? "—"}</span>
  {:else if lastSuccess}
    <span>Updated {lastSuccess}</span>
  {/if}
  {#if wakeNote}<span class="warn">· {wakeNote}</span>{/if}
  <span class="spacer"></span>
  <span>Times and positions are estimated · Powered by TfL Open Data</span>
</footer>

<style>
  .status {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.25rem 0.5rem;
    padding: 0.4rem 1rem;
    font-size: 0.8rem;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }
  .spacer {
    flex: 1;
  }
  .dot {
    width: 0.6rem;
    height: 0.6rem;
    border-radius: 50%;
    background: #bbb;
  }
  .dot.connected {
    background: #2e9d4a;
  }
  .dot.disconnected {
    background: #d23c3c;
  }
  .warn {
    color: var(--warn);
  }
</style>
