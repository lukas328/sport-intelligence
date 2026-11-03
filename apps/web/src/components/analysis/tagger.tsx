"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";
import { CourtHalf, ShotDot } from "./court-half";
import { GoalGrid } from "./goal-grid";

type EventIn = Schemas["EventIn"];
type Outcome = "goal" | "save" | "miss" | "post" | "blocked";
const OUTCOMES: Outcome[] = ["goal", "save", "miss", "post", "blocked"];
const TURNOVERS = ["bad_pass", "catch_error", "steps", "double_dribble", "offensive_foul", "line_violation", "passive_play", "other"] as const;
const HOTKEYS: Record<string, Outcome | "turnover"> = { g: "goal", s: "save", m: "miss", p: "post", t: "turnover" };

export function useRosterNames(orgId: string, teamId: string, seasonId: string) {
  return useQuery({
    queryKey: ["roster", seasonId],
    queryFn: async () =>
      (
        await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
          params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } },
        })
      ).data ?? [],
  });
}

/**
 * Manual event tagging next to the video (BRIEF 7.4): every event gets the current video time, the
 * API maps it to the match clock via the kickoff marks. Hotkeys work while the tagger is open and
 * focus is not in a text field.
 */
export function Tagger({
  orgId,
  match,
  teamName,
  getTime,
}: {
  orgId: string;
  match: Schemas["MatchOut"];
  teamName: string;
  getTime: () => number;
}) {
  const t = useTranslations("events");
  const te = useTranslations("errors");
  const qc = useQueryClient();
  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const [side, setSide] = useState<"own" | "opponent">("own");
  const [player, setPlayer] = useState("");
  const [oppNumber, setOppNumber] = useState("");
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [zone, setZone] = useState<string | null>(null);
  const [penalty, setPenalty] = useState(false);
  const [fastBreak, setFastBreak] = useState(false);
  const [turnoverType, setTurnoverType] = useState<(typeof TURNOVERS)[number]>("bad_pass");
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<ErrorKey | null>(null);
  const path = { org_id: orgId, match_id: match.id };

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["events", match.id] });
    void qc.invalidateQueries({ queryKey: ["stats", match.id] });
    void qc.invalidateQueries({ queryKey: ["match", match.id] });
  };

  const create = useMutation({
    mutationFn: async (body: EventIn) => {
      const { data, error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/events", { params: { path }, body });
      if (error) throw error;
      return data;
    },
    onSuccess: (_d, body) => {
      setFailure(null);
      setNotice(t("saved", { label: labelOf(body), time: formatClock(body.t_ms ?? 0) }));
      setPos(null);
      setZone(null);
      setPenalty(false);
      setFastBreak(false);
      refresh();
    },
    onError: (e) => setFailure(errorKey(e)),
  });

  function labelOf(body: EventIn) {
    if (body.type === "shot") return t(body.outcome as Outcome);
    if (body.type === "turnover") return t("turnover");
    if (body.type === "suspension_2min") return t("suspension");
    if (body.type === "timeout") return t("timeout");
    return t("sevenM");
  }

  function base(type: EventIn["type"]): EventIn {
    const num = oppNumber === "" ? null : Number(oppNumber);
    return {
      type,
      side,
      period: 1,
      t_ms: Math.round(getTime()),
      player_id: side === "own" && player ? player : null,
      number: side === "opponent" ? num : null,
      attributes: {},
    } as EventIn;
  }

  function shot(outcome: Outcome) {
    const b = base("shot");
    create.mutate({
      ...b,
      outcome,
      x: pos?.x ?? null,
      y: pos?.y ?? null,
      goal_zone: (zone as EventIn["goal_zone"]) ?? null,
      shot_type: penalty ? "penalty" : fastBreak ? "fast_break" : null,
    });
  }

  function turnover() {
    create.mutate({ ...base("turnover"), turnover_type: turnoverType, x: pos?.x ?? null, y: pos?.y ?? null });
  }

  async function kickoff(period: number) {
    const ms = Math.round(getTime());
    const { error } = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/kickoff", { params: { path }, body: { period, t_ms: ms } });
    if (error) return setFailure(errorKey(error));
    setFailure(null);
    setNotice(t("kickoffSet", { period, time: formatClock(ms) }));
    refresh();
  }

  async function importFeed(e: ChangeEvent<HTMLInputElement>) {
    const input = e.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const { data, error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/events/import", {
      params: { path },
      // openapi-fetch passes FormData through untouched
      body: body as unknown as { file: string },
      bodySerializer: (b) => b as unknown as FormData,
    });
    input.value = "";
    if (error || !data) return setFailure(errorKey(error));
    setFailure(null);
    setNotice(t("imported", { created: data.created, skipped: data.skipped }));
    refresh();
  }

  // hotkeys (the player owns arrows/space/i/o/d; these letters are free)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)) return;
      const action = HOTKEYS[e.key.toLowerCase()];
      if (!action) return;
      e.preventDefault();
      if (action === "turnover") turnover();
      else shot(action);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const kicked = match.kickoff_ms ?? {};
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto text-sm" data-testid="tagger">
      <div className="flex gap-1" role="group" aria-label={t("side")}>
        {(["own", "opponent"] as const).map((s) => (
          <button
            key={s}
            aria-pressed={side === s}
            onClick={() => setSide(s)}
            className={cn("flex-1 rounded border px-2 py-1.5", side === s ? "border-accent bg-accent text-accent-contrast" : "border-border")}
          >
            {s === "own" ? teamName : match.opponent.name}
          </button>
        ))}
      </div>

      {side === "own" ? (
        <label className="flex flex-col gap-1">
          <span className="font-medium">{t("player")}</span>
          <select value={player} onChange={(e) => setPlayer(e.target.value)} className="min-h-10 rounded-md border border-border bg-background px-2">
            <option value="">{t("noPlayer")}</option>
            {(roster.data ?? [])
              .filter((r) => r.active)
              .sort((a, b) => (a.jersey_number ?? 999) - (b.jersey_number ?? 999))
              .map((r) => (
                <option key={r.player_id} value={r.player_id}>
                  {r.jersey_number != null ? `#${r.jersey_number} ` : ""}
                  {r.first_name} {r.last_name}
                </option>
              ))}
          </select>
        </label>
      ) : (
        <label className="flex flex-col gap-1">
          <span className="font-medium">{t("opponentNumber")}</span>
          <input
            type="number"
            min={0}
            max={99}
            value={oppNumber}
            onChange={(e) => setOppNumber(e.target.value)}
            className="min-h-10 rounded-md border border-border bg-background px-2"
          />
        </label>
      )}

      <div className="flex flex-wrap gap-3">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={penalty} onChange={(e) => (setPenalty(e.target.checked), e.target.checked && setFastBreak(false))} />
          {t("penaltyShot")}
        </label>
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={fastBreak} onChange={(e) => (setFastBreak(e.target.checked), e.target.checked && setPenalty(false))} />
          {t("fastBreak")}
        </label>
      </div>

      <div className="grid grid-cols-3 gap-1" role="group" aria-label={t("tagTitle")}>
        {OUTCOMES.map((o) => (
          <Button key={o} variant={o === "goal" ? "primary" : "secondary"} className="px-2" disabled={create.isPending} onClick={() => shot(o)}>
            {t(o)}
          </Button>
        ))}
        <Button variant="secondary" className="px-2" disabled={create.isPending} onClick={turnover}>
          {t("turnover")}
        </Button>
      </div>
      <label className="flex flex-col gap-1">
        <span className="font-medium">{t("turnoverType")}</span>
        <select
          value={turnoverType}
          onChange={(e) => setTurnoverType(e.target.value as (typeof TURNOVERS)[number])}
          className="min-h-10 rounded-md border border-border bg-background px-2"
        >
          {TURNOVERS.map((k) => (
            <option key={k} value={k}>
              {t(`tt_${k}`)}
            </option>
          ))}
        </select>
      </label>
      <div className="grid grid-cols-3 gap-1">
        <Button variant="ghost" className="px-2" onClick={() => create.mutate(base("suspension_2min"))}>
          {t("suspension")}
        </Button>
        <Button variant="ghost" className="px-2" onClick={() => create.mutate(base("seven_meter_awarded"))}>
          {t("sevenM")}
        </Button>
        <Button variant="ghost" className="px-2" onClick={() => create.mutate(base("timeout"))}>
          {t("timeout")}
        </Button>
      </div>
      <p className="text-xs text-muted">{t("hotkeys")}</p>

      <div className="space-y-1">
        <p className="font-medium">{t("position")}</p>
        <CourtHalf label={t("position")} onPick={(x, y) => setPos({ x, y })}>
          {pos && <ShotDot x={pos.x} y={pos.y} outcome="goal" />}
        </CourtHalf>
      </div>
      <div className="space-y-1">
        <p className="font-medium">{t("goalZone")}</p>
        <GoalGrid mode="pick" selected={zone} onCell={(z) => setZone((cur) => (cur === z ? null : z))} />
      </div>

      <div className="flex flex-wrap gap-1">
        {[1, 2].map((p) => (
          <Button key={p} variant="secondary" className="px-2 text-xs" onClick={() => void kickoff(p)}>
            {kicked[String(p)] != null ? t("kickoffSet", { period: p, time: formatClock(kicked[String(p)]!) }) : t("kickoff", { period: p })}
          </Button>
        ))}
      </div>
      <label className="flex flex-col gap-1">
        <span className="font-medium">{t("import")}</span>
        <input type="file" accept=".csv,.json,text/csv,application/json" onChange={importFeed} className="text-xs" />
      </label>

      <div aria-live="polite">
        {failure && <Alert className="py-2">{te(failure)}</Alert>}
        {notice && (
          <Alert kind="success" className="py-2">
            {notice}
          </Alert>
        )}
      </div>
    </div>
  );
}
