/**
 * Still pictures from a video for the steps that sort what the analysis found (who is who, which
 * colour is whose): one hidden video per file seeks from moment to moment and hands each frame to
 * whoever asked for it. One HLS stream for a whole list, not one player per row; the moments are
 * taken nearest first, so the video mostly seeks forward.
 */

export interface StillBox {
  /** normalised to the picture (0..1): left, top, width, height */
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * The part of the frame (video pixels) a still of a person shows: the person's box with room
 * around it (the box is an estimate from the foot point, ADR on spotlight), in the given aspect
 * ratio (width / height), kept inside the frame.
 */
export function stillRect(box: StillBox, vw: number, vh: number, aspect = 3 / 4, room = 1.6): { sx: number; sy: number; sw: number; sh: number } {
  const cx = (box.x + box.w / 2) * vw;
  const cy = (box.y + box.h / 2) * vh;
  let sh = Math.max(box.h * vh * room, 24);
  let sw = sh * aspect;
  // a crop larger than the frame shrinks to it, keeping the aspect
  const fit = Math.min(1, vw / sw, vh / sh);
  sw *= fit;
  sh *= fit;
  const sx = Math.min(Math.max(0, cx - sw / 2), vw - sw);
  const sy = Math.min(Math.max(0, cy - sh / 2), vh - sh);
  return { sx, sy, sw, sh };
}

type Draw = (video: HTMLVideoElement) => void;
interface Job {
  t: number;
  draw: Draw;
  fail: () => void;
}

const SEEK_TIMEOUT_MS = 8000;
const LOAD_TIMEOUT_MS = 20000;

export class FrameGrabber {
  private readonly video: HTMLVideoElement;
  private readonly ready: Promise<boolean>;
  private queue: Job[] = [];
  private busy = false;
  private destroyHls: (() => void) | null = null;
  private gone = false;

  constructor(src: string, doc: Document = document) {
    const v = doc.createElement("video");
    v.muted = true;
    v.playsInline = true;
    v.preload = "auto";
    this.video = v;
    this.ready = new Promise<boolean>((resolve) => {
      const done = (ok: boolean) => {
        window.clearTimeout(timer);
        resolve(ok);
      };
      const timer = window.setTimeout(() => done(false), LOAD_TIMEOUT_MS);
      v.addEventListener("loadedmetadata", () => done(true), { once: true });
      v.addEventListener("error", () => done(false), { once: true });
    });
    // HLS: native in Safari/iOS, hls.js elsewhere (as the player), with a short buffer: a still
    // needs one frame, not thirty seconds
    if (v.canPlayType("application/vnd.apple.mpegurl")) {
      v.src = src;
    } else {
      void import("hls.js").then(({ default: Hls }) => {
        if (this.gone || !Hls.isSupported()) return;
        const hls = new Hls({ maxBufferLength: 4, maxMaxBufferLength: 8, enableWorker: true });
        hls.loadSource(src);
        hls.attachMedia(v);
        this.destroyHls = () => hls.destroy();
      });
    }
  }

  /** The frame at `tMs` is handed to `draw`; `fail` when it cannot be had. Returns a cancel. */
  grab(tMs: number, draw: Draw, fail: () => void = () => {}): () => void {
    const job: Job = { t: tMs, draw, fail };
    this.queue.push(job);
    void this.pump();
    return () => {
      this.queue = this.queue.filter((j) => j !== job);
    };
  }

  destroy(): void {
    this.gone = true;
    for (const j of this.queue) j.fail();
    this.queue = [];
    this.destroyHls?.();
    this.video.removeAttribute("src");
    this.video.load();
  }

  private async pump(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    try {
      const ok = await this.ready;
      while (this.queue.length && !this.gone) {
        if (!ok) {
          for (const j of this.queue) j.fail();
          this.queue = [];
          break;
        }
        // nearest moment first: the hidden video mostly seeks forward
        const now = this.video.currentTime * 1000;
        this.queue.sort((a, b) => Math.abs(a.t - now) - Math.abs(b.t - now));
        const job = this.queue.shift()!;
        const at = await this.seek(job.t);
        if (this.gone) break;
        if (at) {
          try {
            job.draw(this.video);
          } catch {
            job.fail();
          }
        } else job.fail();
      }
    } finally {
      this.busy = false;
    }
  }

  private seek(tMs: number): Promise<boolean> {
    const v = this.video;
    return new Promise<boolean>((resolve) => {
      const done = (ok: boolean) => {
        window.clearTimeout(timer);
        v.removeEventListener("seeked", onSeeked);
        resolve(ok && v.readyState >= 2 && v.videoWidth > 0);
      };
      const onSeeked = () => done(true);
      const timer = window.setTimeout(() => done(false), SEEK_TIMEOUT_MS);
      v.addEventListener("seeked", onSeeked);
      v.currentTime = Math.max(0, tMs / 1000);
    });
  }
}
