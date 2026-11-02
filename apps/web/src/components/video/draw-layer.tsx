"use client";

import { useEffect, useRef, useState } from "react";
import { drawShapes, type Shape, type Tool } from "./shapes";

/** Interactive drawing surface over the paused video. Coordinates are normalised to 0..1. */
export function DrawLayer({
  tool,
  color,
  shapes,
  onChange,
}: {
  tool: Tool;
  color: string;
  shapes: Shape[];
  onChange: (shapes: Shape[]) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [draft, setDraft] = useState<Shape | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { width, height } = canvas.getBoundingClientRect();
    canvas.width = Math.round(width);
    canvas.height = Math.round(height);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawShapes(ctx, draft ? [...shapes, draft] : shapes, canvas.width, canvas.height);
  }, [shapes, draft]);

  const point = (e: React.PointerEvent<HTMLCanvasElement>): [number, number] => {
    const r = e.currentTarget.getBoundingClientRect();
    const clamp = (v: number) => Math.min(1, Math.max(0, v));
    return [clamp((e.clientX - r.left) / r.width), clamp((e.clientY - r.top) / r.height)];
  };

  return (
    <canvas
      ref={canvasRef}
      data-testid="draw-layer"
      className="absolute inset-0 h-full w-full cursor-crosshair touch-none"
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        const p = point(e);
        setDraft({ kind: tool, points: [p, p], color, width: 4 });
      }}
      onPointerMove={(e) => {
        if (!draft) return;
        const p = point(e);
        setDraft({ ...draft, points: tool === "freehand" ? [...draft.points, p].slice(-500) : [draft.points[0]!, p] });
      }}
      onPointerUp={() => {
        if (draft) onChange([...shapes, draft]);
        setDraft(null);
      }}
    />
  );
}
