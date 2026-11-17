"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { validityMessage } from "@/lib/form-validity";

type Checked = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
const checked = (t: EventTarget | null): t is Checked =>
  t instanceof HTMLInputElement ||
  t instanceof HTMLTextAreaElement ||
  t instanceof HTMLSelectElement;

/**
 * Every form check of the browser (`required`, `type="email"`, `min`) in the app's language
 * instead of the browser's (review R10). One listener for all forms: when a field turns out
 * invalid it gets its message; the next input clears it so the browser checks afresh.
 */
export function FormMessages() {
  const t = useTranslations("formCheck");
  useEffect(() => {
    const onInvalid = (e: Event) => {
      if (!checked(e.target)) return;
      const el = e.target;
      el.setCustomValidity("");
      const m = validityMessage(el);
      if (m) el.setCustomValidity(t(m.key, m.values));
    };
    const onInput = (e: Event) => {
      if (checked(e.target)) e.target.setCustomValidity("");
    };
    document.addEventListener("invalid", onInvalid, true);
    document.addEventListener("input", onInput, true);
    document.addEventListener("change", onInput, true);
    return () => {
      document.removeEventListener("invalid", onInvalid, true);
      document.removeEventListener("input", onInput, true);
      document.removeEventListener("change", onInput, true);
    };
  }, [t]);
  return null;
}
