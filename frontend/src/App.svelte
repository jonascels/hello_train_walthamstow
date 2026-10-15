<script lang="ts">
  // Layout: map plus a panel with the two countdowns and the status bar.
  // Portrait: panel along the bottom. Landscape (the usual tablet board):
  // panel down the right-hand side with the countdowns stacked.
  import { onMount } from "svelte";
  import Countdown from "./components/Countdown.svelte";
  import StatusBar from "./components/StatusBar.svelte";
  import TrainMap from "./components/TrainMap.svelte";
  import { fetchConfig, fetchTrack, type AppConfig, type TrackGeometry } from "./lib/api";
  import { DIRECTION_COLOUR } from "./lib/colors";
  import { live } from "./lib/live.svelte";
  import { theme } from "./lib/theme.svelte";
  import { screenWake } from "./lib/wakeLock.svelte";

  const RETRY_LOAD_MS = 5000;

  let config = $state<AppConfig | null>(null);
  let geometry = $state<TrackGeometry | null>(null);
  let error = $state("");

  const trains = $derived(live.update?.snapshot?.trains ?? []);
  const upTrains = $derived(trains.filter((t) => t.direction === "up"));
  const downTrains = $derived(trains.filter((t) => t.direction === "down"));

  // Countdown labels come from the route's end stations.
  const londonEnd = $derived(geometry?.stations[0].name.replace(/^London /, "") ?? "");
  const countryEnd = $derived(geometry?.stations.at(-1)?.name ?? "");

  // Config and track only need loading once, but keep trying if the backend
  // isn't up yet (e.g. the tablet and server were powered on together).
  async function loadStatic(): Promise<void> {
    while (!geometry) {
      try {
        [config, geometry] = await Promise.all([fetchConfig(), fetchTrack()]);
        error = "";
      } catch (e) {
        error = `Waiting for the server… (${e})`;
        await new Promise((r) => setTimeout(r, RETRY_LOAD_MS));
      }
    }
  }

  onMount(() => {
    loadStatic();
    const stopLive = live.start();
    const stopWake = screenWake.start();
    return () => {
      stopLive();
      stopWake();
    };
  });
</script>

<main class:dark={theme.dark}>
  <div class="map-area">
    {#if config && geometry}
      <!-- Re-create the map when switching light/dark: it needs a new base style. -->
      {#key theme.dark}
        <TrainMap
          {geometry}
          timingBridgeId={config.timing_bridge_id}
          vehicles={live.update?.snapshot?.vehicles ?? []}
          dark={theme.dark}
        />
      {/key}
    {:else}
      <p class="message">{error || "Loading…"}</p>
    {/if}
  </div>
  <div class="panel">
    <div class="countdowns">
      <!-- Liverpool Street is west (left on the map), Chingford east (right). -->
      <Countdown
        label={londonEnd}
        arrow="←"
        colour={DIRECTION_COLOUR.up}
        trains={upTrains}
        now={live.now}
      />
      <Countdown
        label={countryEnd}
        arrow="→"
        colour={DIRECTION_COLOUR.down}
        trains={downTrains}
        now={live.now}
      />
    </div>
    <StatusBar update={live.update} connection={live.connection} wake={screenWake.status} />
  </div>
</main>

<style>
  :global(html, body) {
    margin: 0;
    height: 100%;
    font-family: system-ui, sans-serif;
    overscroll-behavior: none; /* no pull-to-refresh bounce on tablets */
  }
  /* Colours used by all components; .dark overrides them. */
  main {
    --bg: #ffffff;
    --text: #1f2933;
    --muted: #616e7c;
    --border: #e4e7eb;
    --warn: #b25000;
    --passing: #c26b00;
    --shadow: rgb(0 0 0 / 0.1);
  }
  main.dark {
    --bg: #15191e;
    --text: #f0f4f8;
    --muted: #9aa5b1;
    --border: #2d343c;
    --warn: #f0a050;
    --passing: #ffb347;
    --shadow: rgb(0 0 0 / 0.5);
  }
  main {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    color: var(--text);
  }
  .map-area {
    position: relative; /* TrainMap fills this */
    flex: 1;
    min-height: 0;
  }
  .panel {
    display: flex;
    flex-direction: column;
    background: var(--bg);
    box-shadow: 0 -2px 8px var(--shadow);
    z-index: 1;
  }
  .countdowns {
    display: flex;
  }
  .countdowns > :global(:first-child) {
    border-right: 1px solid var(--border);
  }
  .message {
    padding: 2rem;
  }

  /* Landscape tablet: map on the left, countdowns stacked on the right. */
  @media (orientation: landscape) and (min-width: 700px) {
    main {
      flex-direction: row;
    }
    .panel {
      width: clamp(18rem, 34vw, 30rem);
      box-shadow: -2px 0 8px var(--shadow);
    }
    .countdowns {
      flex: 1;
      flex-direction: column;
    }
    .countdowns > :global(:first-child) {
      border-right: none;
      border-bottom: 1px solid var(--border);
    }
  }
</style>
