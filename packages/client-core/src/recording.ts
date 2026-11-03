/**
 * Checks before and during a recording with the phone as camera (addendum 01, 5.2): enough
 * storage for the whole match at 1080p and 50 fps, enough battery, the phone held level.
 */
export const BITRATE_MBPS = 20; // typical H.264 1080p50 bitrate of phone cameras
export const MATCH_MINUTES = 70; // 2 x 30 minutes plus half-time and stoppages
export const MIN_BATTERY = 0.5; // without a charger, half a battery for a match

export function requiredBytes(minutes = MATCH_MINUTES, mbps = BITRATE_MBPS): number {
  return Math.ceil((minutes * 60 * mbps * 1_000_000) / 8);
}

export interface DeviceState {
  freeBytes: number;
  batteryLevel: number | null; // 0..1, null if unknown
  charging: boolean;
}

export type Issue = "storage" | "battery";

export function preflight(d: DeviceState, minutes = MATCH_MINUTES): Issue[] {
  const issues: Issue[] = [];
  // 10 % reserve: the system needs room too
  if (d.freeBytes < requiredBytes(minutes) * 1.1) issues.push("storage");
  if (!d.charging && d.batteryLevel != null && d.batteryLevel < MIN_BATTERY) issues.push("battery");
  return issues;
}

/** Minutes that still fit on the phone at the recording bitrate. */
export function minutesLeft(freeBytes: number, mbps = BITRATE_MBPS): number {
  return Math.floor((freeBytes * 8) / (mbps * 1_000_000 * 60));
}

export type Level = "level" | "tilted_left" | "tilted_right" | "tilted_forward" | "tilted_back";

/**
 * Landscape level from the accelerometer (g units, device axes): the camera should be level
 * sideways (roll within 3 degrees) and roughly upright (pitch within 15 degrees).
 */
export function level(x: number, y: number, z: number): Level {
  const roll = (Math.atan2(y, Math.hypot(x, z)) * 180) / Math.PI;
  const pitch = (Math.atan2(z, Math.abs(x)) * 180) / Math.PI;
  if (roll > 3) return "tilted_right";
  if (roll < -3) return "tilted_left";
  if (pitch > 15) return "tilted_back";
  if (pitch < -15) return "tilted_forward";
  return "level";
}
