// A clock that agrees with the server, so countdowns are right even if the
// tablet's own clock is a minute out. Every message from the server carries
// its time; we remember the difference and add it to Date.now().

let offsetMs = 0;

export function syncClock(serverTimeIso: string): void {
  offsetMs = Date.parse(serverTimeIso) - Date.now();
}

/** Current time in ms since epoch, corrected to the server's clock. */
export function serverNow(): number {
  return Date.now() + offsetMs;
}

const londonTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  hour: "2-digit",
  minute: "2-digit",
});
const londonTimeSecs = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

/** "19:47" in London time (backend times are UTC). */
export const formatTime = (ms: number, seconds = false) =>
  (seconds ? londonTimeSecs : londonTime).format(ms);
