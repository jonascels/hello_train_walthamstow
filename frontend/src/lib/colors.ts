// Shared colours so map icons and countdowns match.
import type { Direction } from "./live.svelte";

export const LINE_COLOUR = "#823a62"; // TfL Weaver line maroon
export const BRIDGE_COLOUR = "#f5a623";
export const DIRECTION_COLOUR: Record<Direction, string> = {
  up: "#1971c2", // towards Liverpool Street
  down: "#2b8a3e", // towards Chingford
};
