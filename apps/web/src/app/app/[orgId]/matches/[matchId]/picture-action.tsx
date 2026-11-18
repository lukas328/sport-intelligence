"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

export type PictureResult = "shared" | "saved" | "failed";

/**
 * The Spielkarte is drawn on the server and takes a few seconds: the button says so while it
 * works, and afterwards what happened (finding A15: three seconds without a reaction).
 */
export function usePictureAction(make?: () => Promise<PictureResult>) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PictureResult | null>(null);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const run = useCallback(async () => {
    if (!make || busy) return;
    window.clearTimeout(timer.current);
    setResult(null);
    setBusy(true);
    const r = await make();
    setBusy(false);
    // shared: the share sheet was the answer; saved or failed: said for a while
    if (r !== "shared") {
      setResult(r);
      timer.current = window.setTimeout(() => setResult(null), 6000);
    }
  }, [make, busy]);
  return { busy, result, run: make ? run : undefined };
}

/** What became of the picture, read out to screen readers too. */
export function PictureStatus({ busy, result }: { busy: boolean; result: PictureResult | null }) {
  const t = useTranslations("anlauf");
  return (
    <span role="status" className="text-[15px] font-semibold" data-testid="picture-status">
      {busy ? t("pictureBusy") : result === "saved" ? t("pictureSaved") : result === "failed" ? t("pictureFailed") : null}
    </span>
  );
}
