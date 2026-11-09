import type { Tone } from "@/components/ui/badge";

/** One plain word about where a match stands, for lists and cards. */
export function matchState(m: { status: string; has_video: boolean; kind?: string }): {
  label: "matches.analysed" | "matches.status_ready" | "matches.status_processing" | "matches.status_uploading" | "matches.status_failed" | "matches.noVideoYet" | "matches.status_scheduled";
  tone: Tone;
} {
  if (m.status === "failed") return { label: "matches.status_failed", tone: "error" };
  if (m.status === "processing") return { label: "matches.status_processing", tone: "accent" };
  if (m.status === "uploading") return { label: "matches.status_uploading", tone: "accent" };
  if (m.status === "ready") return { label: m.has_video ? "matches.analysed" : "matches.status_ready", tone: m.has_video ? "ok" : "neutral" };
  return { label: m.has_video ? "matches.status_scheduled" : "matches.noVideoYet", tone: "neutral" };
}
