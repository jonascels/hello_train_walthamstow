<script lang="ts">
  // Milestone 1 smoke test: proves the dev proxy reaches the backend over
  // both HTTP (/api/config) and WebSocket (/ws).
  import { onMount } from "svelte";

  type Bridge = { id: string; name: string; lat: number; lon: number };

  let lineId = $state("…");
  let bridges = $state<Bridge[]>([]);
  let wsStatus = $state("connecting");
  let serverTime = $state("");

  onMount(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then((cfg) => {
        lineId = cfg.line_id;
        bridges = cfg.bridges;
      })
      .catch(() => (lineId = "backend unreachable"));

    // Same host as the page; Vite proxies /ws to the backend in dev.
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${proto}://${location.host}/ws`);
    socket.onopen = () => (wsStatus = "connected");
    socket.onclose = () => (wsStatus = "disconnected");
    socket.onmessage = (e) => (serverTime = JSON.parse(e.data).server_time);

    return () => socket.close();
  });
</script>

<main>
  <h1>Train Viewer</h1>
  <p>Line: <strong>{lineId}</strong></p>
  <ul>
    {#each bridges as b (b.id)}
      <li>{b.name} ({b.lat}, {b.lon})</li>
    {/each}
  </ul>
  <p>WebSocket: {wsStatus} {serverTime && `· server time ${serverTime}`}</p>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    padding: 2rem;
  }
</style>
