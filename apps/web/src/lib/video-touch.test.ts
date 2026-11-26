import { describe, expect, it, vi } from "vitest";
import { barFraction, enterFullscreen, fullscreenElement, toggleFullscreen } from "./video-touch";

// plain objects stand in for the DOM (the tests run in node)
const box = (extra: Record<string, unknown> = {}, video: Record<string, unknown> | null = null) =>
  ({ tagName: "DIV", querySelector: () => video, ...extra }) as unknown as HTMLElement;

describe("enterFullscreen", () => {
  it("uses the element's fullscreen where there is one", () => {
    const requestFullscreen = vi.fn(() => Promise.resolve());
    expect(enterFullscreen(box({ requestFullscreen }))).toBe("element");
    expect(requestFullscreen).toHaveBeenCalledOnce();
  });

  it("falls back to the prefixed call of older Safari", () => {
    const webkitRequestFullscreen = vi.fn();
    expect(enterFullscreen(box({ webkitRequestFullscreen }))).toBe("element");
    expect(webkitRequestFullscreen).toHaveBeenCalledOnce();
  });

  it("puts the video itself into fullscreen on the iPhone (no element fullscreen there)", () => {
    const webkitEnterFullscreen = vi.fn();
    expect(enterFullscreen(box({}, { webkitEnterFullscreen }))).toBe("video");
    expect(webkitEnterFullscreen).toHaveBeenCalledOnce();
  });

  it("skips the element calls where the browser says fullscreen is off (iPhone Safari)", () => {
    const webkitRequestFullscreen = vi.fn();
    const webkitEnterFullscreen = vi.fn();
    const off = box({ webkitRequestFullscreen, ownerDocument: { fullscreenEnabled: false } }, { webkitEnterFullscreen });
    expect(enterFullscreen(off)).toBe("video");
    expect(webkitRequestFullscreen).not.toHaveBeenCalled();
    expect(webkitEnterFullscreen).toHaveBeenCalledOnce();
  });

  it("does nothing and throws nothing without any way", () => {
    expect(enterFullscreen(box())).toBeNull();
    expect(enterFullscreen(null)).toBeNull();
  });

  it("swallows a refusal instead of an unhandled rejection", async () => {
    const requestFullscreen = vi.fn(() => Promise.reject(new TypeError("Permissions check failed")));
    expect(enterFullscreen(box({ requestFullscreen }))).toBe("element");
    await Promise.resolve();
  });
});

describe("toggleFullscreen", () => {
  it("leaves fullscreen when something is fullscreen, prefixed or not", () => {
    const exitFullscreen = vi.fn(() => Promise.resolve());
    toggleFullscreen(box(), { fullscreenElement: {}, exitFullscreen } as unknown as Document);
    expect(exitFullscreen).toHaveBeenCalledOnce();
    const webkitExitFullscreen = vi.fn();
    toggleFullscreen(box(), { webkitFullscreenElement: {}, webkitExitFullscreen } as unknown as Document);
    expect(webkitExitFullscreen).toHaveBeenCalledOnce();
  });

  it("enters otherwise", () => {
    const webkitEnterFullscreen = vi.fn();
    toggleFullscreen(box({}, { webkitEnterFullscreen }), {} as Document);
    expect(webkitEnterFullscreen).toHaveBeenCalledOnce();
  });

  it("reads the fullscreen element of both spellings", () => {
    expect(fullscreenElement({} as Document)).toBeNull();
    const el = {};
    expect(fullscreenElement({ webkitFullscreenElement: el } as unknown as Document)).toBe(el);
  });
});

describe("barFraction", () => {
  it("maps the finger to the bar and clamps at both ends", () => {
    expect(barFraction(150, 100, 200)).toBe(0.25);
    expect(barFraction(50, 100, 200)).toBe(0);
    expect(barFraction(400, 100, 200)).toBe(1);
    expect(barFraction(10, 0, 0)).toBe(0);
  });
});
