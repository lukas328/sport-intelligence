import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const FIXTURES = path.join(path.dirname(fileURLToPath(import.meta.url)), ".fixtures");
export const MATCH_VIDEO = path.join(FIXTURES, "match.mp4");

/** A 30 s 720p50 test video (~12 MB: noisy, so it needs three 5 MB upload parts). */
export default function globalSetup() {
  mkdirSync(FIXTURES, { recursive: true });
  if (existsSync(MATCH_VIDEO)) return;
  execFileSync("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=50:duration=30",
    "-f", "lavfi", "-i", "anoisesrc=d=30:c=pink:a=0.1",
    "-vf", "noise=alls=40:allf=t",
    "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "3200k", "-c:a", "aac", "-shortest", MATCH_VIDEO,
  ]);
}
