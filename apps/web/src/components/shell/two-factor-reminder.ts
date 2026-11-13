"use client";

import { useEffect, useState } from "react";
import { useOptionalShell } from "./context";

const KEY = "hb_2fa_later_until";
const WEEK = 7 * 24 * 3600 * 1000;

/**
 * The two-factor reminder (UX test H13, OPEN_QUESTIONS Q-AUTH-2b): only once there is something
 * to protect (the server says so in `two_factor_due`), and «Später» puts it away for seven days
 * in this browser.
 */
export function useTwoFactorReminder(): { due: boolean; later: () => void } {
  const shell = useOptionalShell();
  const [snoozed, setSnoozed] = useState(true);
  useEffect(() => {
    try {
      setSnoozed(Number(window.localStorage.getItem(KEY) ?? 0) > Date.now());
    } catch {
      setSnoozed(false);
    }
  }, []);
  return {
    due: Boolean(shell?.me.two_factor_due) && !snoozed,
    later: () => {
      try {
        window.localStorage.setItem(KEY, String(Date.now() + WEEK));
      } catch {
        /* storage unavailable: hidden until the page reloads */
      }
      setSnoozed(true);
    },
  };
}
