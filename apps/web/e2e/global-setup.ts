import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const FIXTURES = path.join(HERE, ".fixtures");
export const MATCH_VIDEO = path.join(FIXTURES, "match.mp4");

/**
 * A 30 s synthetic handball clip (court, players, referees; see packages/vision) re-encoded at a
 * high bitrate (~17 MB) so the upload needs several 5 MB parts. Falls back to an ffmpeg test pattern
 * when the Python workspace is not available.
 */
export default function globalSetup() {
  mkdirSync(FIXTURES, { recursive: true });
  if (existsSync(MATCH_VIDEO)) return;
  const raw = path.join(FIXTURES, "synthetic.mp4");
  let source = raw;
  try {
    execFileSync("uv", ["run", "python", "-m", "handball_vision.synthetic", raw, "--seconds", "30"], {
      cwd: path.resolve(HERE, "../../.."),
      stdio: "ignore",
    });
  } catch {
    source = "testsrc";
  }
  const input = source === "testsrc" ? ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=50:duration=30"] : ["-i", source];
  execFileSync("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y", ...input,
    "-f", "lavfi", "-i", "anoisesrc=d=30:c=pink:a=0.05",
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "8", "-c:a", "aac", "-shortest", MATCH_VIDEO,
  ]);
}
