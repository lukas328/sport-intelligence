/**
 * «Vereinsfarbe wählen» (decision E8): a club that never chose its colour (new and skipped, or made
 * before the choice existed and stored with the old default blue) gets one quiet line on its pages
 * that leads to the choice. Only a club admin sees it (only they can change the colour). «Später»
 * in the onboarding puts it away for this visit (the browser session); closing it puts it away in
 * this browser for good. Choosing a colour ends it everywhere (the API says color_chosen).
 */

const LATER = (org: string) => `hb_colour_hint_later_${org}`;
const OFF = (org: string) => `hb_colour_hint_off_${org}`;

/** The club page with the choice: the hint does not point at the page it stands on. */
export const colourChoicePath = (org: string) => `/app/${org}/club#vereinsfarbe`;

export function shouldOfferColour({
  colorChosen,
  isAdmin,
  later,
  off,
  onChoicePage,
}: {
  colorChosen: boolean;
  isAdmin: boolean;
  /** skipped in the onboarding during this visit */
  later: boolean;
  /** closed in this browser */
  off: boolean;
  onChoicePage: boolean;
}): boolean {
  return !colorChosen && isAdmin && !later && !off && !onChoicePage;
}

function read(storage: () => Storage, key: string): boolean {
  try {
    return storage().getItem(key) != null;
  } catch {
    return false;
  }
}

function write(storage: () => Storage, key: string): void {
  try {
    storage().setItem(key, "1");
  } catch {
    /* storage unavailable: the hint comes back on the next page load */
  }
}

/** What this browser remembers for the club: skipped this visit, closed for good. */
export function storedColourHint(org: string): { later: boolean; off: boolean } {
  return { later: read(() => window.sessionStorage, LATER(org)), off: read(() => window.localStorage, OFF(org)) };
}

/** «Später» in the onboarding: not again during this visit. */
export function skipColourHint(org: string): void {
  write(() => window.sessionStorage, LATER(org));
}

/** Closed by the coach: not again in this browser. */
export function dismissColourHint(org: string): void {
  write(() => window.localStorage, OFF(org));
}
