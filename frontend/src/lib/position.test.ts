import type * as GeoJSON from "geojson";
import { describe, expect, it } from "vitest";
// The real committed track and chainages (loaded by Vite, which Vitest uses).
import geometry from "../../../backend/data/geometry.json";
import trackRaw from "../../../backend/data/track.geojson?raw";
import type { TimingPoint, Vehicle } from "./live.svelte";
import { chainageAt, TrackLine } from "./position";

const track = JSON.parse(trackRaw) as GeoJSON.Feature<GeoJSON.LineString>;
const line = new TrackLine(track, geometry.track_length_m);
const CH: Record<string, number> = Object.fromEntries(
  geometry.stations.map((s) => [s.id, s.chainage_m]),
);

describe("TrackLine", () => {
  it("never throws anywhere along the track, including beyond both ends", () => {
    // Regression: along() threw "coord is required" for negative distances,
    // e.g. looking 20 m behind a train at Liverpool Street (7.9 m), which
    // stopped the whole animation loop.
    for (let m = -100; m <= geometry.track_length_m + 100; m += 25) {
      for (const sign of [1, -1] as const) {
        const [lon, lat] = line.lngLatAt(m);
        expect(Number.isFinite(lon) && Number.isFinite(lat)).toBe(true);
        expect(Number.isFinite(line.bearingAt(m, sign))).toBe(true);
      }
    }
  });

  it("clamps to the ends of the track", () => {
    const coords = track.geometry.coordinates;
    expect(line.lngLatAt(-50)).toEqual(coords[0]);
    expect(line.lngLatAt(geometry.track_length_m + 50)).toEqual(coords.at(-1));
  });

  it("puts a station's chainage on that station", () => {
    const wc = geometry.stations.find((s) => s.id === "910GWLTWCEN")!;
    const [lon, lat] = line.lngLatAt(wc.chainage_m);
    expect(Math.abs(lon - wc.lon)).toBeLessThan(0.001);
    expect(Math.abs(lat - wc.lat)).toBeLessThan(0.001);
  });

  it("gives sensible bearings by the bridge (track runs roughly east–west)", () => {
    const down = line.bearingAt(10321, 1); // towards Chingford: eastwards
    const up = line.bearingAt(10321, -1); // towards London: westwards
    expect(down).toBeGreaterThan(45);
    expect(down).toBeLessThan(135);
    expect(Math.abs(up)).toBeGreaterThan(45);
  });
});

describe("chainageAt", () => {
  const t = (hhmmss: string) => `2026-10-15T${hhmmss}Z`;
  const ms = (hhmmss: string) => Date.parse(t(hhmmss));
  const call = (id: string, arr: string | null, dep: string): TimingPoint => ({
    station_id: id,
    chainage_m: CH[id],
    arr: arr ? t(arr) : null,
    dep: t(dep),
  });
  const vehicle: Vehicle = {
    id: "v1",
    direction: "down",
    destination: "Chingford",
    calls: [
      call("910GWLTWCEN", "19:01:00", "19:01:30"),
      call("910GWDST", "19:04:00", "19:04:30"),
    ],
  };

  it("is unknown before the first known station", () => {
    expect(chainageAt(vehicle, ms("19:00:59"))).toBeNull();
  });

  it("sits at a station while dwelling", () => {
    expect(chainageAt(vehicle, ms("19:01:15"))).toBe(CH["910GWLTWCEN"]);
  });

  it("moves linearly between stations", () => {
    const halfway = (CH["910GWLTWCEN"] + CH["910GWDST"]) / 2;
    expect(chainageAt(vehicle, ms("19:02:45"))).toBeCloseTo(halfway, 6);
  });

  it("stays at the last known station afterwards", () => {
    expect(chainageAt(vehicle, ms("19:10:00"))).toBe(CH["910GWDST"]);
  });

  it("handles a back-calculated station with no arrival time", () => {
    const v = { ...vehicle, calls: [call("910GSTJMSST", null, "18:58:00"), ...vehicle.calls] };
    expect(chainageAt(v, ms("18:58:00"))).toBe(CH["910GSTJMSST"]);
    expect(chainageAt(v, ms("18:57:59"))).toBeNull();
  });

  it("handles a train at Liverpool Street (start of the track)", () => {
    const v: Vehicle = {
      ...vehicle,
      calls: [call("910GLIVST", null, "19:00:00"), call("910GBTHNLGR", "19:03:00", "19:03:30")],
    };
    const chainage = chainageAt(v, ms("19:00:00"))!;
    expect(chainage).toBe(CH["910GLIVST"]);
    expect(Number.isFinite(line.bearingAt(chainage, 1))).toBe(true);
  });
});
