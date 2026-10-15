// Types and fetch helpers for the backend's HTTP API.
import type * as GeoJSON from "geojson";

// Shapes mirror backend/app/services/geometry.py and app/api/routes.py.

export type Bridge = { id: string; name: string; lat: number; lon: number };

export type AppConfig = {
  line_id: string;
  bridges: Bridge[];
  timing_bridge_id: string;
};

// "Chainage" = metres along the track from the London end (Liverpool Street).
export type Station = Bridge & { chainage_m: number };
export type BridgePoint = Bridge & { chainage_m: number };

export type TrackGeometry = {
  line_id: string;
  track_length_m: number;
  stations: Station[]; // ordered by chainage
  bridges: BridgePoint[];
  track: GeoJSON.Feature<GeoJSON.LineString>;
};

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`${path} → HTTP ${resp.status}`);
  return resp.json() as Promise<T>;
}

export const fetchConfig = () => getJson<AppConfig>("/api/config");
export const fetchTrack = () => getJson<TrackGeometry>("/api/track");
