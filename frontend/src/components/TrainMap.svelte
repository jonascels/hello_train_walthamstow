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
  import { loadTrainImage } from "../lib/trainIcon";

  maplibregl.setWorkerUrl(workerUrl);

  let {
    geometry,
    timingBridgeId,
    vehicles,
    dark,
  }: {
    geometry: TrackGeometry;
    timingBridgeId: string;
    vehicles: Vehicle[];
    dark: boolean; // fixed for this map's lifetime; App re-creates it on change
  } = $props();

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

  // Vehicles we've already warned about, so a bad one doesn't flood the console.
  const warned = new Set<string>();

  // Current estimated position of every vehicle we can place.
  function trainFeatures(track: TrackLine, nowMs: number) {
    const features: GeoJSON.Feature<GeoJSON.Point>[] = [];
    for (const v of vehicles) {
      // One train with odd data must never stop the others being drawn.
      try {
        const chainage = chainageAt(v, nowMs);
        if (chainage === null || !Number.isFinite(chainage)) continue;
        // The icon is drawn facing east (bearing 90°). Rotate it to follow the
        // track; if that would turn it upside down, use the mirrored
        // (west-facing) icon instead and rotate that.
        const bearing = track.bearingAt(chainage, v.direction === "down" ? 1 : -1);
        const fromEast = ((bearing - 90 + 540) % 360) - 180; // −180…180
        const facing = Math.abs(fromEast) <= 90 ? "right" : "left";
        const rotate = facing === "right" ? fromEast : ((fromEast + 360) % 360) - 180;
        features.push({
          type: "Feature",
          properties: { icon: `train-${v.direction}-${facing}`, rotate },
          geometry: { type: "Point", coordinates: track.lngLatAt(chainage) },
        });
      } catch (e) {
        if (!warned.has(v.id)) {
          warned.add(v.id);
          console.warn(`Can't place train ${v.id}; skipping it`, e, v);
        }
      }
    }
    return { type: "FeatureCollection", features } as GeoJSON.FeatureCollection;
  }

  onMount(() => {
    // Map colours that change with light/dark mode.
    const c = dark
      ? { station: "#15191e", label: "#e4e7eb", halo: "#15191e", bridgeLabel: "#ffc46b" }
      : { station: "#ffffff", label: "#333333", halo: "#ffffff", bridgeLabel: "#b26b00" };
    const track = new TrackLine(geometry.track, geometry.track_length_m);
    let frame = 0;
    const timingBridge = geometry.bridges.find((b) => b.id === timingBridgeId)!;
    const lons = geometry.bridges.map((b) => b.lon);
    const westernmost = lons.indexOf(Math.min(...lons));

    const map = new maplibregl.Map({
      container,
      style: `https://tiles.openfreemap.org/styles/${dark ? "dark" : "positron"}`,
      center: [timingBridge.lon, timingBridge.lat],
      zoom: 14,
      attributionControl: { compact: true },
    });

    map.on("load", async () => {
      // One image per direction (colour) and facing. Rasterised at 2× so
      // they stay crisp on high-DPI tablet screens.
      for (const direction of ["up", "down"] as const) {
        for (const facing of ["left", "right"] as const) {
          const img = await loadTrainImage(DIRECTION_COLOUR[direction], facing, 2);
          map.addImage(`train-${direction}-${facing}`, img, { pixelRatio: 2 });
        }
      }

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
          "circle-color": c.station,
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
        paint: { "text-color": c.label, "text-halo-color": c.halo, "text-halo-width": 2 },
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
          "circle-color": ["case", ["get", "timing"], BRIDGE_COLOUR, c.station],
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
        paint: { "text-color": c.bridgeLabel, "text-halo-color": c.halo, "text-halo-width": 2 },
      });

      // Fit the view to the stations near the timing bridge.
      const nearby = geometry.stations.filter(
        (s) => Math.abs(s.chainage_m - timingBridge.chainage_m) <= VIEW_RADIUS_M,
      );
      const bounds = new maplibregl.LngLatBounds();
      for (const p of [...nearby, timingBridge]) bounds.extend([p.lon, p.lat]);
      map.fitBounds(bounds, { padding: 60, animate: false });

      // Train icons (cartoon trains), on top of everything else.
      map.addSource("trains", { type: "geojson", data: trainFeatures(track, serverNow()) });
      map.addLayer({
        id: "trains",
        type: "symbol",
        source: "trains",
        layout: {
          "icon-image": ["get", "icon"],
          "icon-rotate": ["get", "rotate"],
          "icon-rotation-alignment": "map",
          "icon-size": 0.75,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
        },
      });

      // Animation loop: recompute positions from the clock every frame.
      // No server round-trip; the snapshot only changes every ~30 s.
      const source = map.getSource("trains") as maplibregl.GeoJSONSource;
      let lastDraw = 0;
      const draw = (frameTime: number) => {
        // Schedule the next frame first, so an error in this one can't stop
        // the animation for good (which would freeze every train).
        frame = requestAnimationFrame(draw);
        if (frameTime - lastDraw >= FRAME_MS) {
          lastDraw = frameTime;
          source.setData(trainFeatures(track, serverNow()));
        }
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
