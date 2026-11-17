"use client";

import { useMutation } from "@tanstack/react-query";
import { CalendarCheck, ClipboardList, Dumbbell, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { DialogContent, DialogRoot } from "@/components/ui/dialog";
import { api } from "@/lib/client";

/** Switch «Teamleben» (the team setting `team_features`) on or off for one team. */
export function useTeamLife(orgId: string, teamId: string, initial: boolean) {
  const router = useRouter();
  const [on, setOn] = useState(initial);
  const save = useMutation({
    mutationFn: async (next: boolean) => {
      const { error } = await api.PATCH("/v1/orgs/{org_id}/teams/{team_id}", {
        params: { path: { org_id: orgId, team_id: teamId } },
        body: { settings: { team_features: next } },
      });
      if (error) throw new Error("save");
      return next;
    },
    onSuccess: (next) => {
      setOn(next);
      router.refresh();
    },
  });
  return { on, save };
}

/**
 * What «Teamleben» brings, before it is switched on (finding K16): what comes, who sees what,
 * what players and parents need, and that switching off deletes nothing.
 */
export function TeamLifeDialog({
  open,
  onOpenChange,
  teamName,
  busy,
  failed,
  onConfirm,
  inviteHref,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  teamName: string;
  busy: boolean;
  failed: boolean;
  onConfirm: () => void;
  inviteHref?: string | null;
}) {
  const t = useTranslations("teamLife");
  const comes: [ReactNode, string, string][] = [
    [<CalendarCheck key="d" />, t("datesTitle"), t("datesText")],
    [<Dumbbell key="p" />, t("planTitle"), t("planText")],
    [<ClipboardList key="a" />, t("tasksTitle"), t("tasksText")],
    [<Users key="o" />, t("ownTitle"), t("ownText")],
  ];
  return (
    <DialogRoot open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("dialogTitle", { team: teamName })} description={t("dialogIntro")} wide>
        <div className="space-y-6" data-testid="team-life-dialog">
          <section aria-labelledby="tl-comes">
            <h3 id="tl-comes" className="mb-2 text-[15px] font-bold">
              {t("comesTitle")}
            </h3>
            <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
              {comes.map(([icon, title, text]) => (
                <li key={title} className="flex gap-3 border-t border-rule pt-3">
                  <span aria-hidden className="mt-0.5 text-ink-2 [&_svg]:size-5">
                    {icon}
                  </span>
                  <span>
                    <span className="block font-bold">{title}</span>
                    <span className="block text-[15px] text-ink-2">{text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="tl-who">
            <h3 id="tl-who" className="mb-2 text-[15px] font-bold">
              {t("whoTitle")}
            </h3>
            <table className="w-full border-collapse text-[15px]">
              <tbody>
                {(["coaches", "players", "parents"] as const).map((k) => (
                  <tr key={k} className="border-t border-rule align-top">
                    <th scope="row" className="w-[9.5rem] py-2 pr-3 text-left font-bold">
                      {t(`who_${k}`)}
                    </th>
                    <td className="py-2">{t(`sees_${k}`)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section aria-labelledby="tl-need" className="border-l-4 border-attn pl-3">
            <h3 id="tl-need" className="m-0 text-[15px] font-bold">
              {t("needTitle")}
            </h3>
            <p className="mt-1 mb-0 text-[15px]">{t("needText")}</p>
          </section>
          <p className="m-0 text-[15px] text-ink-2">{t("offText")}</p>
          {failed && <Alert>{t("failed")}</Alert>}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={onConfirm} loading={busy} data-testid="team-life-confirm">
              {t("switchOn")}
            </Button>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              {t("notNow")}
            </Button>
            {inviteHref && (
              <Link href={inviteHref} className={linkClass}>
                {t("inviteFirst")}
              </Link>
            )}
          </div>
        </div>
      </DialogContent>
    </DialogRoot>
  );
}

/** «Teamleben ausschalten?»: nothing is deleted, it is only out of sight. */
export function TeamLifeOffDialog({ open, onOpenChange, busy, onConfirm }: { open: boolean; onOpenChange: (open: boolean) => void; busy: boolean; onConfirm: () => void }) {
  const t = useTranslations("teamLife");
  return (
    <DialogRoot open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("offTitle")} description={t("offText")}>
        <div className="flex flex-wrap gap-3">
          <Button onClick={onConfirm} loading={busy} data-testid="team-life-off-confirm">
            {t("switchOff")}
          </Button>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            {t("keepOn")}
          </Button>
        </div>
      </DialogContent>
    </DialogRoot>
  );
}

/**
 * The switch where the coach looks for it (K16): a block on the Team page. Off: what it is and
 * «Teamleben einschalten» (with the dialog). On: one line and the way there, «Ausschalten» quiet.
 */
export function TeamLifeCard({ orgId, teamId, teamName, initial, inviteHref }: { orgId: string; teamId: string; teamName: string; initial: boolean; inviteHref?: string | null }) {
  const t = useTranslations("teamLife");
  const { on, save } = useTeamLife(orgId, teamId, initial);
  const [ask, setAsk] = useState(false);
  const [askOff, setAskOff] = useState(false);
  return (
    <section aria-labelledby="team-life" data-testid="team-life-card">
      <SectionHead as="h2" title={<span id="team-life">{t("name")}</span>} />
      {on ? (
        <>
          <p className="m-0 text-[15px]">{t("onText")}</p>
          <p className="mt-3 mb-0 flex flex-wrap gap-x-5 gap-y-1">
            <Link href={`/app/${orgId}/schedule`} className={linkClass}>
              {t("open")}
            </Link>
            <button type="button" className="min-h-11 cursor-pointer text-[15px] text-ink-2 underline decoration-[1.5px] underline-offset-4" onClick={() => setAskOff(true)}>
              {t("switchOff")}
            </button>
          </p>
        </>
      ) : (
        <>
          <p className="m-0 text-[15px]">{t("offPitch")}</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={() => setAsk(true)} data-testid="team-life-open">
            {t("switchOnShort")}
          </Button>
        </>
      )}
      <TeamLifeDialog
        open={ask}
        onOpenChange={setAsk}
        teamName={teamName}
        busy={save.isPending}
        failed={save.isError}
        inviteHref={inviteHref}
        onConfirm={() => save.mutate(true, { onSuccess: () => setAsk(false) })}
      />
      <TeamLifeOffDialog open={askOff} onOpenChange={setAskOff} busy={save.isPending} onConfirm={() => save.mutate(false, { onSuccess: () => setAskOff(false) })} />
    </section>
  );
}
