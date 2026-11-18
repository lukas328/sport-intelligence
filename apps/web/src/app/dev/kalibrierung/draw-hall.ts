/**
 * The drawn hall image of the calibration component page: a wooden floor seen from the camera of
 * lib/synthetic-hall, the handball lines in white and a volleyball court in blue, a little grain.
 * Invented, no real hall and no people.
 */
import { COURT } from "@handball/court";
import { HALL_H, HALL_SIZE, project } from "@/lib/synthetic-hall";

/** Draws the hall into a 2D context of HALL_SIZE. */
export function drawHall(ctx: CanvasRenderingContext2D): void {
  const [W, H] = HALL_SIZE;
  // the wall and the stands at the back, the floor in front
  ctx.fillStyle = "rgb(58 62 70)";
  ctx.fillRect(0, 0, W, H);
  const floor = (x: number, y: number) => project(HALL_H, x, y);
  ctx.beginPath();
  [floor(-12, -4), floor(52, -4), floor(52, 26), floor(-12, 26)].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
  ctx.fillStyle = "rgb(190 150 100)";
  ctx.fill();
  // the court area a little darker
  ctx.beginPath();
  [floor(0, 0), floor(40, 0), floor(40, 20), floor(0, 20)].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
  ctx.fillStyle = "rgb(176 134 86)";
  ctx.fill();
  const stroke = (pts: readonly (readonly [number, number])[], colour: string, width: number, dash: number[] = []) => {
    ctx.beginPath();
    ctx.setLineDash(dash);
    pts.forEach(([x, y], i) => {
      const [u, v] = floor(x, y);
      if (i) ctx.lineTo(u, v);
      else ctx.moveTo(u, v);
    });
    ctx.strokeStyle = colour;
    ctx.lineWidth = width;
    ctx.stroke();
    ctx.setLineDash([]);
  };
  // a volleyball court in blue (another sport's lines are always there)
  stroke([[11, 1.5], [29, 1.5], [29, 18.5], [11, 18.5], [11, 1.5]], "rgb(40 80 170)", 2.5);
  stroke([[20, 1.5], [20, 18.5]], "rgb(40 80 170)", 2.5);
  for (const [name, pts] of Object.entries(COURT.lines)) stroke(pts, "rgb(240 240 236)", 3, COURT.dashedLines.includes(name) ? [14, 10] : []);
  // goals
  for (const gx of [0, 40]) {
    const [a, b] = [floor(gx, 8.5), floor(gx, 11.5)];
    ctx.strokeStyle = "rgb(230 60 50)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(a[0], a[1]);
    ctx.lineTo(a[0], a[1] - 52);
    ctx.lineTo(b[0], b[1] - 44);
    ctx.lineTo(b[0], b[1]);
    ctx.stroke();
  }
  // grain
  const img = ctx.getImageData(0, 0, W, H);
  let s = 11;
  for (let i = 0; i < img.data.length; i += 4) {
    s = (s * 16807) % 2147483647;
    const g = (s / 2147483647 - 0.5) * 14;
    img.data[i] = img.data[i]! + g;
    img.data[i + 1] = img.data[i + 1]! + g;
    img.data[i + 2] = img.data[i + 2]! + g;
  }
  ctx.putImageData(img, 0, 0);
}
