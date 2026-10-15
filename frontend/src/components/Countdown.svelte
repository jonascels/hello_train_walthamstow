<script lang="ts">
  // One direction's countdown to the next train at the bridge.
  import { formatTime } from "../lib/clock";
  import type { Train } from "../lib/live.svelte";
  import { trainSvgUrl } from "../lib/trainIcon";

  let {
    label,
    arrow,
    colour,
    trains,
    now,
  }: {
    label: string; // where trains in this direction are heading
    arrow: "←" | "→";
    colour: string; // matches this direction's train icons on the map
    trains: Train[]; // this direction only, soonest first
    now: number; // server-corrected ms
  } = $props();

  // Show "Passing now" for this long after the estimated time, then move on.
  const PASSING_MS = 20_000;

  const upcoming = $derived(
    trains
      .map((t) => ({ ...t, ms: Date.parse(t.t_bridge) }))
      .filter((t) => t.ms > now - PASSING_MS),
  );
  const next = $derived(upcoming[0]);
  const after = $derived(upcoming[1]);
  const secondsLeft = $derived(next ? Math.round((next.ms - now) / 1000) : 0);

  function mmss(totalSeconds: number): string {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }
</script>

<section class="countdown">
  <h2>
    {#if arrow === "←"}
      <img class="train" src={trainSvgUrl(colour, "left")} alt="" />
      {`← ${label}`}
    {:else}
      {`${label} →`}
      <img class="train" src={trainSvgUrl(colour, "right")} alt="" />
    {/if}
  </h2>
  {#if !next}
    <p class="time none">—</p>
    <p class="sub">No trains due</p>
  {:else if secondsLeft <= 0}
    <p class="time passing">Passing now</p>
    <p class="sub">{after ? `then ${formatTime(after.ms)}` : ""}&nbsp;</p>
  {:else}
    <p class="time">{mmss(secondsLeft)}</p>
    <p class="sub">
      at {formatTime(next.ms, true)}{after ? ` · then ${formatTime(after.ms)}` : ""}
    </p>
  {/if}
</section>

<style>
  .countdown {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0.75rem 1rem;
    text-align: center;
    /* Big enough to read across a room; scales with the screen. */
    --time-size: clamp(3rem, 11vmin, 7.5rem);
  }
  h2 {
    margin: 0;
    font-size: clamp(1.1rem, 3.2vmin, 1.8rem);
    font-weight: 600;
  }
  .train {
    height: 1.6em;
    margin: 0 0.3em;
    vertical-align: -0.35em;
  }
  /* Its dark outline disappears on a dark panel; add a soft glow. */
  :global(main.dark) .train {
    filter: drop-shadow(0 0 2px rgb(255 255 255 / 0.6));
  }
  .time {
    margin: 0.1rem 0;
    font-size: var(--time-size);
    font-weight: 700;
    font-variant-numeric: tabular-nums; /* digits don't jiggle as they change */
    line-height: 1.1;
  }
  .passing {
    color: var(--passing);
    /* Smaller text, same line height, so the layout doesn't jump. */
    font-size: calc(var(--time-size) * 0.6);
    line-height: calc(var(--time-size) * 1.1);
  }
  .none {
    color: var(--muted);
  }
  .sub {
    margin: 0;
    color: var(--muted);
    font-size: clamp(0.95rem, 2.6vmin, 1.4rem);
  }
</style>
