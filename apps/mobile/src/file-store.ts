import { File, Paths } from "expo-file-system";

/** Synchronous key-value store on disk for the marks queue (survives app restarts, offline). */
export const fileStore = {
  getItem(key: string): string | null {
    const f = new File(Paths.document, `${key}.json`);
    try {
      return f.exists ? f.textSync() : null;
    } catch {
      return null;
    }
  },
  setItem(key: string, value: string): void {
    new File(Paths.document, `${key}.json`).write(value);
  },
};
