"use client";

import { useQuery } from "@tanstack/react-query";
import { Check } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { useShell } from "@/components/shell/context";
import { api } from "@/lib/client";
import { coachRights } from "@/lib/roles";
import { cn } from "@/lib/utils";
import { InviteDialog } from "./invite-dialog";

const KEY = (team: string) => `hb_next_steps_hidden:${team}`;

/**
 * After registering and taking over a team (finding K17): three clear next steps for the coach,
 * each with its way: the first video, the Co-Trainer, a link for the team chat without an account.
 * Each ticks off from the real data; the block goes away when all are done or when put away.
 */
export function NextSteps({ hasVideo }: { hasVideo: boolean }) {
  const t = useTranslations("nextSteps");
  const { org, team } = useShell();
  const coach = team ? coachRights(org.my_role, team.my_role) : false;
  const [hidden, setHidden] = useState(true);
  const [invite, setInvite] = useState(false);
  useEffect(() => {
    if (!team) return;
    try {
      setHidden(window.localStorage.getItem(KEY(team.id)) === "1");
    } catch {
      setHidden(false);
    }
  }, [team]);
  const path = { org_id: org.id, team_id: team?.id ?? "" };
  const people = useQuery({
    queryKey: ["next-steps-people", team?.id],
    enabled: coach && !hidden && Boolean(team),
    queryFn: async () => {
      const [members, invitations] = await Promise.all([
        api.GET("/v1/orgs/{org_id}/teams/{team_id}/members", { params: { path } }),
        api.GET("/v1/orgs/{org_id}/invitations", { params: { path: { org_id: org.id }, query: { team_id: path.team_id } } }),
      ]);
      const coaches = (members.data ?? []).filter((m) => m.person_role === "trainer" || m.person_role === "co_trainer").length;
      const invited = (invitations.data ?? []).some((i) => !i.revoked_at && i.team_role !== "player" && i.team_role !== "parent");
      return coaches > 1 || invited;
    },
  });
  const shared = useQuery({
    queryKey: ["next-steps-shared", team?.id],
    enabled: coach && !hidden && Boolean(team),
    queryFn: async () => ((await api.GET("/v1/orgs/{org_id}/teams/{team_id}/share-links", { params: { path } })).data ?? []).length > 0,
  });
  if (!team || !coach || hidden || people.isPending || shared.isPending) return null;
  const base = `/app/${org.id}/teams/${team.id}`;
  const act = cn(linkClass, "inline-flex min-h-11 items-center");
  const steps = [
    { key: "video", done: hasVideo, action: <Link href={`${base}/matches?upload=1`} className={act}>{t("videoAction")}</Link> },
    {
      key: "coach",
      done: Boolean(people.data),
      action: (
        <button type="button" className={cn(act, "cursor-pointer")} onClick={() => setInvite(true)} data-testid="next-invite">
          {t("coachAction")}
        </button>
      ),
    },
    { key: "share", done: Boolean(shared.data), action: <Link href={hasVideo ? `${base}/scenes` : `${base}/collections`} className={act}>{t("shareAction")}</Link> },
  ] as const;
  if (steps.every((s) => s.done)) return null;
  return (
    <section aria-labelledby="next-steps" data-testid="next-steps">
      <SectionHead title={<span id="next-steps">{t("title")}</span>} />
      <ol className="m-0 list-none p-0">
        {steps.map((s, i) => (
          <li key={s.key} className="grid grid-cols-[28px_minmax(0,1fr)] gap-x-3 border-t border-rule py-3">
            <span aria-hidden className={cn("font-num grid size-7 place-items-center text-[17px]", s.done ? "bg-ink text-ground" : "border-2 border-ink")}>
              {s.done ? <Check className="size-4" strokeWidth={3} /> : i + 1}
            </span>
            <span>
              <span className={cn("block font-bold", s.done && "text-ink-2 line-through decoration-1")}>
                {t(`${s.key}Title`)}
                {s.done && <span className="sr-only"> {t("done")}</span>}
              </span>
              {!s.done && (
                <>
                  <span className="block text-[15px] text-ink-2">{t(`${s.key}Text`)}</span>
                  <span className="mt-1 block">{s.action}</span>
                </>
              )}
            </span>
          </li>
        ))}
      </ol>
      <button
        type="button"
        className="mt-1 min-h-11 cursor-pointer text-[15px] text-ink-2 underline decoration-[1.5px] underline-offset-4"
        onClick={() => {
          try {
            window.localStorage.setItem(KEY(team.id), "1");
          } catch {
            /* storage unavailable: hidden until the page reloads */
          }
          setHidden(true);
        }}
      >
        {t("hide")}
      </button>
      <InviteDialog orgId={org.id} team={{ id: team.id, name: team.name, team_features: team.team_features }} isAdmin={org.my_role === "org_admin"} open={invite} onOpenChange={setInvite} />
    </section>
  );
}
