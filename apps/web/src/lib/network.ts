/** Connection hints (addendum 01, 4.8: poor hall Wi-Fi, mobile data). */
interface NetInfo {
  type?: string;
  saveData?: boolean;
  effectiveType?: string;
}

/** "mobile" on cellular or data saver, "slow" on 2G/3G-like links, else null. Unknown = null. */
export function connectionHint(nav: { connection?: NetInfo } = globalThis.navigator as never): "mobile" | "slow" | null {
  const c = nav?.connection;
  if (!c) return null;
  if (c.type === "cellular" || c.saveData) return "mobile";
  if (c.effectiveType && ["slow-2g", "2g", "3g"].includes(c.effectiveType)) return "slow";
  return null;
}
