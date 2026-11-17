"use client";

import { useEffect, useRef, type RefObject } from "react";

/** Files the input already holds, or null. Taken as an array, so clearing the input afterwards
 * does not empty the list. */
export function heldFiles(el: { files: ArrayLike<File> | null } | null | undefined): File[] | null {
  const files = el?.files;
  return files && files.length > 0 ? Array.from(files) : null;
}

/** A file chosen before React hydrated (slow phone, first visit) changed the input while no one
 * was listening: the browser still holds it, the app never heard of it and the upload was
 * silently lost. On mount this hands such files to `onFiles` once (StrictMode runs effects twice). */
export function useEarlyFiles(ref: RefObject<HTMLInputElement | null>, onFiles: (files: File[]) => void) {
  const handler = useRef(onFiles);
  handler.current = onFiles;
  const taken = useRef(false);
  useEffect(() => {
    if (taken.current) return;
    taken.current = true;
    const files = heldFiles(ref.current);
    if (files) handler.current(files);
  }, [ref]);
}
