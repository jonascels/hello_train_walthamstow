// Follows the device's light/dark setting (e.g. a tablet set to switch to
// dark mode at night) and updates live when it changes.

const query = window.matchMedia("(prefers-color-scheme: dark)");

class Theme {
  dark = $state(query.matches);

  constructor() {
    query.addEventListener("change", (e) => (this.dark = e.matches));
  }
}

export const theme = new Theme();
