/**
 * Fullscreen and scrubbing that also work on a phone.
 *
 * iPhone Safari has no fullscreen for elements (`requestFullscreen` is missing there): only the
 * video itself can go fullscreen, with `webkitEnterFullscreen` and the phone's own controls. Older
 * Safari on the iPad and the Mac knows the prefixed `webkitRequestFullscreen`. A refusal (no user
 * gesture, not allowed in a frame) never surfaces as an error on the page.
 */

type FsElement = HTMLElement & { webkitRequestFullscreen?: () => Promise<void> | void };
type FsDocument = Document & {
  webkitFullscreenEnabled?: boolean;
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void> | void;
};
type FsVideo = HTMLVideoElement & { webkitEnterFullscreen?: () => void };

function settle(result: unknown): void {
  if (result && typeof (result as Promise<void>).catch === "function") (result as Promise<void>).catch(() => {});
}

/** The element that is fullscreen now, prefixed or not. */
export function fullscreenElement(doc: Document): Element | null {
  const d = doc as FsDocument;
  return d.fullscreenElement ?? d.webkitFullscreenElement ?? null;
}

/**
 * Puts `box` into fullscreen; on the iPhone the video inside it. Returns how: "element", "video"
 * or null when the browser offers neither.
 */
export function enterFullscreen(box: HTMLElement | null | undefined): "element" | "video" | null {
  if (!box) return null;
  const el = box as FsElement;
  const doc = box.ownerDocument as FsDocument | undefined;
  // a browser that says element fullscreen is off (iPhone) goes straight to the video
  const allowed = (doc?.fullscreenEnabled ?? doc?.webkitFullscreenEnabled) !== false;
  try {
    if (allowed && typeof el.requestFullscreen === "function") {
      settle(el.requestFullscreen());
      return "element";
    }
    if (allowed && typeof el.webkitRequestFullscreen === "function") {
      settle(el.webkitRequestFullscreen());
      return "element";
    }
    const video = (box.tagName === "VIDEO" ? box : box.querySelector("video")) as FsVideo | null;
    if (video && typeof video.webkitEnterFullscreen === "function") {
      video.webkitEnterFullscreen();
      return "video";
    }
  } catch {
    // refused: the page stays as it is
  }
  return null;
}

/** Leaves fullscreen when something is fullscreen, else puts `box` into it. */
export function toggleFullscreen(box: HTMLElement | null | undefined, doc: Document): void {
  const d = doc as FsDocument;
  if (fullscreenElement(d)) {
    try {
      settle(typeof d.exitFullscreen === "function" ? d.exitFullscreen() : d.webkitExitFullscreen?.());
    } catch {
      // nothing to leave
    }
    return;
  }
  enterFullscreen(box);
}

/** The place under a finger on a horizontal bar, from 0 (left end) to 1 (right end). */
export function barFraction(clientX: number, left: number, width: number): number {
  if (!(width > 0)) return 0;
  return Math.min(1, Math.max(0, (clientX - left) / width));
}
