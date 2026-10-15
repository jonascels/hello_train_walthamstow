<script lang="ts">
  // Layout: the map fills the screen; a panel along the bottom holds the two
  // countdowns and the status bar.
  import { onMount } from "svelte";
  import Countdown from "./components/Countdown.svelte";
  import StatusBar from "./components/StatusBar.svelte";
  import TrainMap from "./components/TrainMap.svelte";
  import { fetchConfig, fetchTrack, type AppConfig, type TrackGeometry } from "./lib/api";
  import { live } from "./lib/live.svelte";

  let config = $state<AppConfig | null>(null);
  let geometry = $state<TrackGeometry | null>(null);
  let error = $state("");

  const trains = $derived(live.update?.snapshot?.trains ?? []);
  const upTrains = $derived(trains.filter((t) => t.direction === "up"));
  const downTrains = $derived(trains.filter((t) => t.direction === "down"));

  // Countdown labels come from the route's end stations.
  const londonEnd = $derived(geometry?.stations[0].name.replace(/^London /, "") ?? "");
  const countryEnd = $derived(geometry?.stations.at(-1)?.name ?? "");

  onMount(() => {
    Promise.all([fetchConfig(), fetchTrack()])
      .then(([c, g]) => ([config, geometry] = [c, g]))
      .catch((e) => (error = `Could not reach the backend: ${e}`));
    return live.start(); // returned function disconnects on unmount
  });
</script>

<main>
  <div class="map-area">
    {#if config && geometry}
      <TrainMap {geometry} timingBridgeId={config.timing_bridge_id} />
    {:else}
      <p class="message">{error || "Loading…"}</p>
    {/if}
  </div>
  <div class="panel">
    <div class="countdowns">
      <!-- Liverpool Street is west (left on the map), Chingford east (right). -->
      <Countdown label={londonEnd} arrow="←" trains={upTrains} now={live.now} />
      <Countdown label={countryEnd} arrow="→" trains={downTrains} now={live.now} />
    </div>
    <StatusBar update={live.update} connection={live.connection} />
  </div>
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
    display: flex;
    flex-direction: column;
  }
  .map-area {
    position: relative; /* TrainMap fills this */
    flex: 1;
  }
  .panel {
    background: #fff;
    box-shadow: 0 -2px 8px rgb(0 0 0 / 0.1);
    z-index: 1;
  }
  .countdowns {
    display: flex;
  }
  .countdowns > :global(:first-child) {
    border-right: 1px solid #eee;
  }
  .message {
    padding: 2rem;
  }
</style>
