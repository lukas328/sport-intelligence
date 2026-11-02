export type Tool = "arrow" | "line" | "circle" | "freehand" | "spotlight";

export interface Shape {
  kind: Tool | "text";
  points: [number, number][]; // normalised 0..1
  color: string;
  width: number;
  text?: string | null;
}

/** Draws shapes (normalised coordinates) onto a canvas of the video's displayed size. */
export function drawShapes(ctx: CanvasRenderingContext2D, shapes: Shape[], w: number, h: number) {
  for (const s of shapes) {
    const pts = s.points.map(([x, y]) => [x * w, y * h] as const);
    ctx.lineWidth = s.width * (w / 1000) + 1;
    ctx.strokeStyle = s.color;
    ctx.fillStyle = s.color;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const [a, b] = [pts[0], pts[pts.length - 1]];
    if (!a || !b) continue;
    if (s.kind === "spotlight") {
      const r = Math.hypot(b[0] - a[0], b[1] - a[1]);
      ctx.save();
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      ctx.beginPath();
      ctx.rect(0, 0, w, h);
      ctx.arc(a[0], a[1], Math.max(r, 10), 0, Math.PI * 2, true);
      ctx.fill("evenodd");
      ctx.restore();
      ctx.beginPath();
      ctx.arc(a[0], a[1], Math.max(r, 10), 0, Math.PI * 2);
      ctx.stroke();
    } else if (s.kind === "circle") {
      ctx.beginPath();
      ctx.ellipse((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, Math.abs(b[0] - a[0]) / 2 || 1, Math.abs(b[1] - a[1]) / 2 || 1, 0, 0, Math.PI * 2);
      ctx.stroke();
    } else if (s.kind === "freehand") {
      ctx.beginPath();
      pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]);
      ctx.lineTo(b[0], b[1]);
      ctx.stroke();
      if (s.kind === "arrow") {
        const angle = Math.atan2(b[1] - a[1], b[0] - a[0]);
        const head = 10 + ctx.lineWidth * 3;
        ctx.beginPath();
        ctx.moveTo(b[0], b[1]);
        ctx.lineTo(b[0] - head * Math.cos(angle - 0.45), b[1] - head * Math.sin(angle - 0.45));
        ctx.lineTo(b[0] - head * Math.cos(angle + 0.45), b[1] - head * Math.sin(angle + 0.45));
        ctx.closePath();
        ctx.fill();
      }
    }
  }
}
