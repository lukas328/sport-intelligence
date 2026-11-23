"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { matchSides } from "@/lib/match-sides";
import { storedUploadIds } from "@/lib/upload";
import type { LocalUpload } from "@/lib/upload-store";
import { durationParts, finishAt, headlineKey, isActive, type FileProgress, type MatchProgress } from "@/lib/progress";

/** The unfinished uploads this browser started, read after mount and when the uploads change. */
export function useStoredUploads(local: LocalUpload[]): Set<string> {
  const [ids, setIds] = useState<Set<string>>(() => new Set());
  useEffect(() => setIds(storedUploadIds()), [local]);
  return ids;
}

/** The sentences of the progress, one place for the head, Spiele and the match. */
export function useProgressWords() {
  const t = useTranslations("progress");
  const tParts = useTranslations("parts");
  const tUpload = useTranslations("upload");
  const format = useFormatter();
  const clock = (d: Date) => format.dateTime(d, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

  /** «noch etwa 1 Std. 35 Min.» */
  const left = (seconds: number) => {
    const { h, m } = durationParts(seconds);
    if (!h) return t("leftMin", { m });
    return m ? t("leftHours", { h, m }) : t("leftHoursOnly", { h });
  };

  /** «fertig etwa um 20:15» (with the day when it is not today) */
  const finish = (seconds: number, now = Date.now()) => {
    const at = finishAt(seconds, now);
    const sameDay = new Date(now).toDateString() === at.toDateString();
    return sameDay ? t("finishAt", { time: clock(at) }) : t("finishAtDay", { day: format.dateTime(at, { weekday: "long" }), time: clock(at) });
  };

  /** The time sentence of a match: the finish when known, else the time left in the step. */
  const when = (p: MatchProgress, now = Date.now()): string | null => {
    if (!isActive(p)) return null;
    if (p.eta_s != null) return p.stage === "upload" ? left(p.eta_s) : finish(p.eta_s, now);
    const f = p.files.find((x) => x.stage === p.stage && x.eta_s != null);
    return f?.eta_s != null ? `${t(`step_${f.stage}`)}: ${left(f.eta_s)}` : null;
  };

  const headline = (p: MatchProgress) => t(headlineKey(p) as "headAnalysis");

  /** «TV Gegner», or for a video of the opponent both teams, home team first as on the match's
   * page (BUG-18): «HC Dritte gegen TV Gegner» */
  const matchName = (p: Pick<MatchProgress, "opponent_name" | "scouting_other" | "kind"> & { is_home?: boolean }) => {
    if (!(p.kind === "scouting" && p.scouting_other)) return p.opponent_name || t("training");
    const sides = matchSides(p, { team: "", opponent: p.opponent_name });
    return t("scoutingName", { home: sides.home, away: sides.away });
  };

  /** «1. Halbzeit», «Teil 2», «Torkamera links» or the file name */
  const fileName = (f: FileProgress, files: FileProgress[]) => {
    if (f.part != null) {
      const halves = files.some((x) => x.half != null);
      return halves && f.half != null ? tParts("half", { n: f.half }) : files.filter((x) => x.part != null).length > 1 ? tParts("part", { n: f.part }) : f.filename;
    }
    return f.role !== "main" ? tUpload(`role_${f.role}`) : f.filename;
  };

  const percent = (v: number) => t("percent", { n: Math.floor(v * 100) });

  return { t, left, finish, when, headline, matchName, fileName, percent, clock };
}
