"use client";

import { useEffect, useState } from "react";

/** True below 640 px: the tactics camera shows the attacked half there (UX test B51). */
export function usePhone(): boolean {
  const [phone, setPhone] = useState(false);
  useEffect(() => {
    const q = window.matchMedia("(max-width: 640px)");
    const on = () => setPhone(q.matches);
    on();
    q.addEventListener("change", on);
    return () => q.removeEventListener("change", on);
  }, []);
  return phone;
}
