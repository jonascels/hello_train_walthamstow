// Where is a train right now? Everything here is an ESTIMATE: TfL only gives
// times at stations, so between stations we assume constant speed.

import { along } from "@turf/along";
import { length } from "@turf/length";
import type * as GeoJSON from "geojson";
import type { Vehicle } from "./live.svelte";

/**
 * Chainage (metres from the London end) of `vehicle` at time `nowMs`,
 * or null if we can't place it (it hasn't reached its first known station).
 *
 * Calls are in travel order. At each station the train sits still from `arr`
 * to `dep`; between stations it moves linearly from `dep` to the next `arr`.
 */
export function chainageAt(vehicle: Vehicle, nowMs: number): number | null {
  const calls = vehicle.calls.map((c) => ({
    m: c.chainage_m,
    dep: Date.parse(c.dep!), // backend always sets dep on vehicle calls
    arr: c.arr ? Date.parse(c.arr) : Date.parse(c.dep!),
  }));
  if (calls.length === 0 || nowMs < calls[0].arr) return null;

  for (let i = 0; i < calls.length; i++) {
    const here = calls[i];
    if (nowMs <= here.dep) return here.m; // at (or arriving at) this station
    const next = calls[i + 1];
    if (!next) return here.m; // past its last known station: leave it there
    if (nowMs < next.arr) {
      const fraction = (nowMs - here.dep) / (next.arr - here.dep);
      return here.m + fraction * (next.m - here.m);
    }
  }
  return calls[calls.length - 1].m;
}

/** Converts chainage to map coordinates along the track line. */
export class TrackLine {
  #line: GeoJSON.Feature<GeoJSON.LineString>;
  #scale: number;

  constructor(line: GeoJSON.Feature<GeoJSON.LineString>, trackLengthM: number) {
    this.#line = line;
    // Chainage is in British National Grid metres; Turf measures on the
    // globe. They differ by ~0.04% here, so rescale to keep stations on spot.
    this.#scale = length(line, { units: "meters" }) / trackLengthM;
  }

  lngLatAt(chainageM: number): [number, number] {
    const point = along(this.#line, chainageM * this.#scale, { units: "meters" });
    return point.geometry.coordinates as [number, number];
  }

  /**
   * Compass bearing (degrees clockwise from north) of travel at `chainageM`,
   * for a train moving towards higher chainage (sign +1) or lower (sign −1).
   */
  bearingAt(chainageM: number, sign: 1 | -1): number {
    const LOOK_M = 20;
    const [lon1, lat1] = this.lngLatAt(chainageM - sign * LOOK_M);
    const [lon2, lat2] = this.lngLatAt(chainageM + sign * LOOK_M);
    // Flat-earth approximation is plenty over 40 m.
    const dx = (lon2 - lon1) * Math.cos((lat1 * Math.PI) / 180);
    const dy = lat2 - lat1;
    return (Math.atan2(dx, dy) * 180) / Math.PI;
  }
}
