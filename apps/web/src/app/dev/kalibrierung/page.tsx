import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CalibrationDemo } from "./demo";

export const metadata: Metadata = { title: "Kalibrierung", robots: { index: false } };

/**
 * The court calibration dialog on a drawn hall image, without a video (component page for the
 * design check and the e2e test of the dialog). Development only: shown in production with
 * HB_DEV_PAGES=1. ?state=hall (court from an earlier video of the hall), auto (automatic
 * suggestion), missing (no court) or confirmed (a court confirmed before).
 */
export default async function CalibrationPage({ searchParams }: { searchParams: Promise<{ state?: string }> }) {
  if (process.env.NODE_ENV === "production" && process.env.HB_DEV_PAGES !== "1") notFound();
  const { state } = await searchParams;
  const s = state === "auto" || state === "missing" || state === "confirmed" ? state : "hall";
  return <CalibrationDemo state={s} />;
}
