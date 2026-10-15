<script lang="ts">
  // The map: base tiles, the track, stations and the two bridges.
  // Train icons are added in milestone 6.
  import * as maplibregl from "maplibre-gl";
  import type * as GeoJSON from "geojson";
  import "maplibre-gl/dist/maplibre-gl.css";
  // MapLibre finds its web worker relative to its own file, which breaks once
  // Vite bundles it. Let Vite bundle the worker and hand MapLibre the URL.
  import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
  import { onMount } from "svelte";
  import type { TrackGeometry } from "../lib/api";

  maplibregl.setWorkerUrl(workerUrl);

  let { geometry, timingBridgeId }: { geometry: TrackGeometry; timingBridgeId: string } =
    $props();

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

  onMount(() => {
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
        // Weaver line maroon (TfL brand colour).
        paint: { "line-color": "#823a62", "line-width": 5 },
      });

      map.addSource("stations", { type: "geojson", data: pointsFeature(geometry.stations) });
      map.addLayer({
        id: "stations",
        type: "circle",
        source: "stations",
        paint: {
          "circle-radius": 6,
          "circle-color": "#ffffff",
          "circle-stroke-color": "#823a62",
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
          "circle-color": ["case", ["get", "timing"], "#f5a623", "#ffffff"],
          "circle-stroke-color": "#f5a623",
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
    });

    return () => map.remove();
  });
</script>

<div class="map" bind:this={container}></div>

<style>
  .map {
    position: absolute;
    inset: 0;
  }
</style>
