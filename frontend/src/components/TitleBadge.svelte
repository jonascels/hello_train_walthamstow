<script lang="ts">
  // The app's title, floating over the top-left corner of the map.
  import "@fontsource/fredoka/600.css"; // bundled, so it works offline too
  import { LINE_COLOUR } from "../lib/colors";
  import { trainSvgUrl } from "../lib/trainIcon";
</script>

<h1 class="badge" style:--line={LINE_COLOUR}>
  <img src={trainSvgUrl("#f5a623", "right")} alt="" />
  Hello Train!
</h1>

<style>
  .badge {
    position: absolute;
    top: max(0.75rem, env(safe-area-inset-top));
    left: max(0.75rem, env(safe-area-inset-left));
    z-index: 1;
    margin: 0;
    padding: 0.3em 0.7em 0.3em 0.5em;
    display: flex;
    align-items: center;
    gap: 0.35em;
    font-family: "Fredoka", system-ui, sans-serif;
    font-weight: 600;
    font-size: clamp(1.3rem, 4.2vmin, 2.4rem);
    color: #fff;
    background: var(--line);
    border: 3px solid #fff;
    border-radius: 999px;
    box-shadow: 0 3px 10px rgb(0 0 0 / 0.25);
    transform: rotate(-2deg); /* a little jaunty */
    pointer-events: none; /* don't block dragging the map */
    user-select: none;
  }
  img {
    height: 1.1em;
  }
</style>
