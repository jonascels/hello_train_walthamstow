<script lang="ts">
  // The map: base tiles, the track, stations, the two bridges and moving
  // train icons at their ESTIMATED positions (see lib/position.ts).
  import * as maplibregl from "maplibre-gl";
  import type * as GeoJSON from "geojson";
  import "maplibre-gl/dist/maplibre-gl.css";
  // MapLibre finds its web worker relative to its own file, which breaks once
  // Vite bundles it. Let Vite bundle the worker and hand MapLibre the URL.
  import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
  import { onMount } from "svelte";
  import type { TrackGeometry } from "../lib/api";
  import { serverNow } from "../lib/clock";
  import { BRIDGE_COLOUR, DIRECTION_COLOUR, LINE_COLOUR } from "../lib/colors";
  import type { Vehicle } from "../lib/live.svelte";
  import { chainageAt, TrackLine } from "../lib/position";

  maplibregl.setWorkerUrl(workerUrl);

  let {
    geometry,
    timingBridgeId,
    vehicles,
  }: { geometry: TrackGeometry; timingBridgeId: string; vehicles: Vehicle[] } = $props();

  // Redraw train positions at most this often (they move ~1 m per 50 ms).
  const FRAME_MS = 50;

  // How much track either side of the timing bridge the initial view shows.
  const VIEW_RADIUS_M = 3000;
  const FONT = ["Noto Sans Regular"]; // must exist in the OpenFreeMap style's glyphs

  let container: HTMLDivElement;

  // GeoJSON points for stations/bridges, with properties the layers style on.
  function pointsFeature(
    points: { lon: number; lat: number; name: string }[],
    extra: (i: number) => Record<string, unknown> = () => ({}),
  ): GeoJSON.FeatureCollection<GeoJSON.Point> {
    return {
      type: "FeatureCollection",
      features: points.map((p, i) => ({
        type: "Feature",
        properties: { name: p.name, ...extra(i) },
        geometry: { type: "Point", coordinates: [p.lon, p.lat] },
      })),
    };
  }

  // Current estimated position of every vehicle we can place.
  function trainFeatures(track: TrackLine, nowMs: number) {
    const features: GeoJSON.Feature<GeoJSON.Point>[] = [];
    for (const v of vehicles) {
      const chainage = chainageAt(v, nowMs);
      if (chainage === null) continue;
      features.push({
        type: "Feature",
        properties: { direction: v.direction, destination: v.destination },
        geometry: { type: "Point", coordinates: track.lngLatAt(chainage) },
      });
    }
    return { type: "FeatureCollection", features } as GeoJSON.FeatureCollection;
  }

  onMount(() => {
    const track = new TrackLine(geometry.track, geometry.track_length_m);
    let frame = 0;
    const timingBridge = geometry.bridges.find((b) => b.id === timingBridgeId)!;
    const lons = geometry.bridges.map((b) => b.lon);
    const westernmost = lons.indexOf(Math.min(...lons));

    const map = new maplibregl.Map({
      container,
      style: "https://tiles.openfreemap.org/styles/positron",
      center: [timingBridge.lon, timingBridge.lat],
      zoom: 14,
      attributionControl: { compact: true },
    });

    map.on("load", () => {
      map.addSource("track", { type: "geojson", data: geometry.track });
      map.addLayer({
        id: "track",
        type: "line",
        source: "track",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": LINE_COLOUR, "line-width": 5 },
      });

      map.addSource("stations", { type: "geojson", data: pointsFeature(geometry.stations) });
      map.addLayer({
        id: "stations",
        type: "circle",
        source: "stations",
        paint: {
          "circle-radius": 6,
          "circle-color": "#ffffff",
          "circle-stroke-color": LINE_COLOUR,
          "circle-stroke-width": 3,
        },
      });
      map.addLayer({
        id: "station-labels",
        type: "symbol",
        source: "stations",
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT,
          "text-size": 14,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
        },
        paint: { "text-color": "#333", "text-halo-color": "#fff", "text-halo-width": 2 },
      });

      map.addSource("bridges", {
        type: "geojson",
        data: pointsFeature(geometry.bridges, (i) => ({
          timing: geometry.bridges[i].id === timingBridgeId,
          // The bridges are ~90 m apart, so their labels would collide: put the
          // westernmost bridge's label to its left and the others' to their right.
          anchor: i === westernmost ? "bottom-right" : "bottom-left",
        })),
      });
      map.addLayer({
        id: "bridges",
        type: "circle",
        source: "bridges",
        paint: {
          // The timing bridge (West Ave) is larger and filled.
          "circle-radius": ["case", ["get", "timing"], 9, 6],
          "circle-color": ["case", ["get", "timing"], BRIDGE_COLOUR, "#ffffff"],
          "circle-stroke-color": BRIDGE_COLOUR,
          "circle-stroke-width": 3,
        },
      });
      map.addLayer({
        id: "bridge-labels",
        type: "symbol",
        source: "bridges",
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT,
          "text-size": 13,
          "text-anchor": ["get", "anchor"],
          // Nudge up and away from the dot, towards the side the label is on.
          "text-offset": [
            "case",
            ["==", ["get", "anchor"], "bottom-right"],
            ["literal", [-0.4, -0.6]],
            ["literal", [0.4, -0.6]],
          ],
          "text-allow-overlap": true,
        },
        paint: { "text-color": "#b26b00", "text-halo-color": "#fff", "text-halo-width": 2 },
      });

      // Fit the view to the stations near the timing bridge.
      const nearby = geometry.stations.filter(
        (s) => Math.abs(s.chainage_m - timingBridge.chainage_m) <= VIEW_RADIUS_M,
      );
      const bounds = new maplibregl.LngLatBounds();
      for (const p of [...nearby, timingBridge]) bounds.extend([p.lon, p.lat]);
      map.fitBounds(bounds, { padding: 60, animate: false });

      // Train icons, on top of everything else.
      map.addSource("trains", { type: "geojson", data: trainFeatures(track, serverNow()) });
      map.addLayer({
        id: "trains",
        type: "circle",
        source: "trains",
        paint: {
          "circle-radius": 9,
          "circle-color": [
            "match",
            ["get", "direction"],
            "up",
            DIRECTION_COLOUR.up,
            DIRECTION_COLOUR.down,
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 3,
        },
      });

      // Animation loop: recompute positions from the clock every frame.
      // No server round-trip; the snapshot only changes every ~30 s.
      const source = map.getSource("trains") as maplibregl.GeoJSONSource;
      let lastDraw = 0;
      const draw = (frameTime: number) => {
        if (frameTime - lastDraw >= FRAME_MS) {
          source.setData(trainFeatures(track, serverNow()));
          lastDraw = frameTime;
        }
        frame = requestAnimationFrame(draw);
      };
      frame = requestAnimationFrame(draw);
    });

    return () => {
      cancelAnimationFrame(frame);
      map.remove();
    };
  });
</script>

<div class="map" bind:this={container}></div>

<style>
  .map {
    position: absolute;
    inset: 0;
  }
</style>
