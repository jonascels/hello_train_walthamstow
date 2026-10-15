<script lang="ts">
  // Layout: map fills the screen; countdowns (milestone 5) will sit on top.
  import { onMount } from "svelte";
  import TrainMap from "./components/TrainMap.svelte";
  import { fetchConfig, fetchTrack, type AppConfig, type TrackGeometry } from "./lib/api";

  let config = $state<AppConfig | null>(null);
  let geometry = $state<TrackGeometry | null>(null);
  let error = $state("");

  onMount(async () => {
    try {
      [config, geometry] = await Promise.all([fetchConfig(), fetchTrack()]);
    } catch (e) {
      error = `Could not reach the backend: ${e}`;
    }
  });
</script>

<main>
  {#if config && geometry}
    <TrainMap {geometry} timingBridgeId={config.timing_bridge_id} />
  {:else}
    <p class="message">{error || "Loading…"}</p>
  {/if}
</main>

<style>
  :global(html, body) {
    margin: 0;
    height: 100%;
    font-family: system-ui, sans-serif;
  }
  main {
    position: fixed;
    inset: 0;
  }
  .message {
    padding: 2rem;
  }
</style>
