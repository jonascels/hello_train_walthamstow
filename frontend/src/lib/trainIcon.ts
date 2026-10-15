// A little cartoon steam train, drawn as SVG so it can be any colour.
// Used for the map icons and the countdown headings.

export type Facing = "left" | "right";

const OUTLINE = "#1f2933";

/** SVG markup for a train in `colour`, facing `facing`. 64×44 units. */
export function trainSvg(colour: string, facing: Facing, scale = 1): string {
  const w = 64 * scale;
  const h = 44 * scale;
  // Drawn facing right; mirror the whole drawing for a left-facing train.
  const flip = facing === "left" ? 'transform="translate(64 0) scale(-1 1)"' : "";
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 64 44">
  <g ${flip} stroke="${OUTLINE}" stroke-width="1.6" stroke-linejoin="round">
    <!-- puff of smoke -->
    <circle cx="33" cy="5" r="3.2" fill="#fff" stroke="#9aa5b1" stroke-width="1"/>
    <circle cx="27.5" cy="3.6" r="2.4" fill="#fff" stroke="#9aa5b1" stroke-width="1"/>
    <!-- chimney -->
    <rect x="39" y="7" width="7" height="11" rx="1" fill="#3e4c59"/>
    <rect x="37.5" y="4.5" width="10" height="4" rx="1.5" fill="#3e4c59"/>
    <!-- boiler -->
    <rect x="22" y="15" width="34" height="17" rx="8" fill="${colour}"/>
    <rect x="34" y="15" width="3" height="17" fill="#f5c542" stroke-width="1"/>
    <!-- cab with roof and window -->
    <rect x="5" y="9" width="21" height="23" rx="3" fill="${colour}"/>
    <rect x="3" y="5.5" width="25" height="5" rx="2" fill="#3e4c59"/>
    <rect x="9" y="13" width="13" height="9" rx="2" fill="#dff3ff"/>
    <!-- smiley face on the front -->
    <circle cx="55" cy="23.5" r="7.5" fill="#ffe8a8"/>
    <circle cx="53" cy="21.5" r="1.1" fill="${OUTLINE}" stroke="none"/>
    <circle cx="57.4" cy="21.5" r="1.1" fill="${OUTLINE}" stroke="none"/>
    <path d="M52 25.5 q3.2 3 6.4 0" fill="none" stroke-width="1.3" stroke-linecap="round"/>
    <!-- chassis, cowcatcher and wheels -->
    <rect x="3" y="31" width="54" height="4.5" rx="2" fill="#3e4c59"/>
    <path d="M57 31 L63 38.5 L56 38.5 Z" fill="#7b8794"/>
    ${[13, 29, 45]
      .map(
        (x) =>
          `<circle cx="${x}" cy="37" r="5.8" fill="#323f4b"/>` +
          `<circle cx="${x}" cy="37" r="1.8" fill="#e4e7eb" stroke="none"/>`,
      )
      .join("")}
  </g>
</svg>`;
}

/** The SVG as a URL usable in <img src> or as a map image. */
export const trainSvgUrl = (colour: string, facing: Facing, scale = 1) =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(trainSvg(colour, facing, scale))}`;

/** Loads the SVG as an image element (for MapLibre's addImage). */
export async function loadTrainImage(
  colour: string,
  facing: Facing,
  scale: number,
): Promise<HTMLImageElement> {
  const img = new Image();
  img.src = trainSvgUrl(colour, facing, scale);
  await img.decode();
  return img;
}
