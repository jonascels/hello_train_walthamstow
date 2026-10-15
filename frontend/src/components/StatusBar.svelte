<script lang="ts">
  // Connection state, data freshness and attribution.
  import { formatTime } from "../lib/clock";
  import type { Connection, LiveUpdate } from "../lib/live.svelte";

  let { update, connection }: { update: LiveUpdate | null; connection: Connection } =
    $props();

  const lastSuccess = $derived(
    update?.last_success ? formatTime(Date.parse(update.last_success), true) : null,
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
  <span class="spacer"></span>
  <span>Times and positions are estimated · Powered by TfL Open Data</span>
</footer>

<style>
  .status {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.4rem 1rem;
    font-size: 0.8rem;
    color: #666;
    border-top: 1px solid #eee;
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
    color: #b25000;
  }
</style>
