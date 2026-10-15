<script lang="ts">
  // One direction's countdown to the next train at the bridge.
  import { formatTime } from "../lib/clock";
  import type { Train } from "../lib/live.svelte";

  let {
    label,
    arrow,
    trains,
    now,
  }: {
    label: string; // where trains in this direction are heading
    arrow: "←" | "→";
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
  <h2>{arrow === "←" ? `← ${label}` : `${label} →`}</h2>
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
    padding: 0.75rem 1rem;
    text-align: center;
  }
  h2 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
    color: #823a62; /* Weaver line */
  }
  .time {
    margin: 0.1rem 0;
    font-size: 3.5rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums; /* digits don't jiggle as they change */
    line-height: 1.1;
  }
  .passing {
    color: #c26b00;
    font-size: 2.4rem;
    line-height: 1.6;
  }
  .none {
    color: #999;
  }
  .sub {
    margin: 0;
    color: #555;
    font-size: 0.95rem;
  }
</style>
