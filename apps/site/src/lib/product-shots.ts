/**
 * The product pictures in public/product, made by scripts/product-shots (capture.mjs, then
 * compose.mjs). Their sizes and callouts come from product-shots.json, which compose.mjs writes,
 * so the pages stay right when the pictures are made again.
 */
import manifest from "./product-shots.json";

export type ShotName = keyof typeof manifest;

/** Where a label sits ("r" right of its point, "tl" above and running right …). */
export type Place = "r" | "l" | "t" | "b" | "tl" | "tr" | "bl" | "br";

export type Callout = {
  id: string;
  /** the label's point, in per cent of the picture */
  from: [number, number];
  /** the spot the arrow points at, in per cent */
  to: [number, number];
  place: Place;
  bend: number;
};

export type Shot = {
  name: ShotName;
  width: number;
  height: number;
  src: string;
  srcSet: string;
  callouts: Callout[];
};

export function productShot(name: ShotName): Shot {
  const m = manifest[name] as { width: number; height: number; callouts: Callout[] };
  return {
    name,
    width: m.width,
    height: m.height,
    src: `/product/${name}.webp`,
    srcSet: `/product/${name}.webp ${m.width}w, /product/${name}@2x.webp ${m.width * 2}w`,
    callouts: m.callouts,
  };
}

/**
 * The arrow of a callout in pixels of the 1x picture: a curve from the label to just before the
 * spot, and its head. The same curve compose.mjs draws for its previews.
 */
export function arrow(c: Callout, width: number, height: number): { line: string; head: string } {
  const ax = (c.from[0] / 100) * width;
  const ay = (c.from[1] / 100) * height;
  const tx = (c.to[0] / 100) * width;
  const ty = (c.to[1] / 100) * height;
  const mx = (ax + tx) / 2 - (ty - ay) * c.bend;
  const my = (ay + ty) / 2 + (tx - ax) * c.bend;
  // stop a little before the spot, so the head does not cover it
  const dx = tx - mx;
  const dy = ty - my;
  const len = Math.hypot(dx, dy) || 1;
  const ex = tx - (dx / len) * 5;
  const ey = ty - (dy / len) * 5;
  const ux = dx / len;
  const uy = dy / len;
  const size = 13;
  const wing = (s: number) => {
    const a = (s * 28 * Math.PI) / 180;
    const rx = ux * Math.cos(a) - uy * Math.sin(a);
    const ry = ux * Math.sin(a) + uy * Math.cos(a);
    return `${(ex - rx * size).toFixed(1)} ${(ey - ry * size).toFixed(1)}`;
  };
  const f = (v: number) => v.toFixed(1);
  return {
    line: `M${f(ax)} ${f(ay)}Q${f(mx)} ${f(my)} ${f(ex)} ${f(ey)}`,
    head: `M${wing(1)}L${f(ex)} ${f(ey)}L${wing(-1)}`,
  };
}
