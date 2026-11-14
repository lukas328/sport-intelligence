/** The sentences that depend on MULTI_FILE, filled into the texts as {pause}, {upload}, {fileNeed}, {fileNot}. */
import type { Messages } from "@/messages/de";
import { MULTI_FILE } from "@/lib/site";

export function fileVars(m: Messages): Record<string, string> {
  return {
    pause: MULTI_FILE ? m.filming.pauseMulti : m.filming.pause,
    upload: MULTI_FILE ? m.filming.uploadMulti : m.filming.upload,
    fileNeed: MULTI_FILE ? m.facts.fileNeedMulti : m.facts.fileNeed,
    fileNot: MULTI_FILE ? "" : m.facts.fileNot,
  };
}

/** «Das noch nicht»: the item about a second file only while it is true. */
export function notList(m: Messages): string[] {
  return MULTI_FILE ? m.honest.not : [...m.honest.not, m.honest.notFiles];
}
