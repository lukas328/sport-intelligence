"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { CourtLines } from "@/components/domain/court-lines";
import { clubStyle } from "@/lib/color";
import { useState, type FormEvent } from "react";
import { InviteForm } from "@/components/people/invite-form";
import { RosterEditor } from "@/components/roster/roster-editor";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Checkbox, Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { OfficialTeamSearch } from "./team-search";
import { errorKey, fieldErrors, type ErrorKey } from "@/lib/errors";

type Org = Schemas["OrgOut"];
type Team = Schemas["TeamOut"];
const STEPS = ["stepClub", "stepTeam", "stepRoster", "stepInvite"] as const;
const COUNTRIES = ["CH", "DE", "AT", "FR", "LI"] as const;

export function OnboardingWizard({ existingOrg }: { existingOrg?: Org }) {
  const t = useTranslations();
  const router = useRouter();
  const [step, setStep] = useState(existingOrg ? 1 : 0);
  const [org, setOrg] = useState<Org | undefined>(existingOrg);
  const [team, setTeam] = useState<Team | undefined>();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  // the club colour as it is being picked: the welcome band shows it right away
  const [colour, setColour] = useState(existingOrg?.primary_color ?? "#0b6bcb");
  const [name, setName] = useState(existingOrg?.name ?? "");
  // a new coach first looks for the team in the official data; a club by hand on request
  const [manual, setManual] = useState(false);
  // a team taken over from the official data: club and team are there, the squad is next
  const [claimed, setClaimed] = useState(false);
  const shownStep = claimed ? 2 : step;

  async function createOrg(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    const { data, error } = await api.POST("/v1/orgs", {
      body: {
        name: String(f.get("name")),
        country: String(f.get("country")),
        primary_color: String(f.get("primary_color")),
        secondary_color: String(f.get("secondary_color")),
      },
    });
    if (error || !data) {
      setBusy(false);
      setFields(fieldErrors(error));
      return setError(errorKey(error));
    }
    const logo = f.get("logo");
    if (logo instanceof File && logo.size > 0) {
      const body = new FormData();
      body.append("file", logo);
      const res = await api.PUT("/v1/orgs/{org_id}/logo", {
        params: { path: { org_id: data.id } },
        body: body as unknown as { file: string },
        bodySerializer: (b) => b as unknown as FormData,
      });
      if (res.error) setError(errorKey(res.error));
    }
    setBusy(false);
    setOrg(data);
    setStep(1);
  }

  async function createTeam(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!org) return;
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    const league = String(f.get("league") ?? "").trim();
    const { data, error } = await api.POST("/v1/orgs/{org_id}/teams", {
      params: { path: { org_id: org.id } },
      body: {
        name: String(f.get("name")),
        gender: String(f.get("gender")) as Team["gender"],
        is_youth: f.get("is_youth") === "on",
        league: league || null,
      },
    });
    setBusy(false);
    if (error || !data) {
      setFields(fieldErrors(error));
      return setError(errorKey(error));
    }
    setTeam(data);
    setStep(2);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <header className="club relative overflow-hidden rounded-lg bg-club px-6 pt-6 pb-5 text-club-ink transition-colors duration-300 sm:px-8 sm:pt-8" style={clubStyle(colour) as CSSProperties}>
        <CourtLines className="absolute right-0 bottom-0 hidden aspect-square h-full sm:block" />
        <div className="relative">
          <p className="text-[0.9375rem] font-semibold">{t("onboarding.progress", { step: shownStep + 1, total: STEPS.length })}</p>
          <h1 className="mt-1 text-[2.5rem] leading-[0.95] sm:text-5xl">{name.trim() || t("onboarding.title")}</h1>
          <ol className="mt-6 flex max-w-md gap-2" aria-label={t("onboarding.progress", { step: shownStep + 1, total: STEPS.length })}>
            {STEPS.map((s, i) => (
              <li key={s} aria-current={i === shownStep ? "step" : undefined} className={`flex-1 space-y-1.5 text-xs ${i <= shownStep ? "font-semibold" : "opacity-75"}`}>
                <span aria-hidden className={`block h-1 rounded-full ${i <= shownStep ? "bg-club-ink" : "bg-club-ink/30"}`} />
                {t(`onboarding.${s}`)}
              </li>
            ))}
          </ol>
        </div>
      </header>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}

      {step === 0 && !manual && <OfficialTeamSearch onManual={() => setManual(true)} onClaimed={(club) => (setName(club), setClaimed(true))} />}

      {step === 0 && manual && (
        <Card>
          <form onSubmit={createOrg} className="space-y-4" noValidate>
            <p className="text-muted">{t("onboarding.clubIntro")}</p>
            <Input label={t("onboarding.clubName")} name="name" required autoFocus error={fields.name} value={name} onChange={(e) => setName(e.target.value)} />
            <Select label={t("onboarding.country")} name="country" defaultValue="CH">
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {t(`onboarding.countries.${c}`)}
                </option>
              ))}
            </Select>
            <div className="grid grid-cols-2 gap-3">
              <Input label={t("onboarding.primaryColor")} name="primary_color" type="color" value={colour} onChange={(e) => setColour(e.target.value)} className="h-11 w-24 p-1" />
              <Input label={t("onboarding.secondaryColor")} name="secondary_color" type="color" defaultValue="#ffffff" className="h-11 w-24 p-1" />
            </div>
            <Input
              label={`${t("onboarding.logo")} (${t("common.optional")})`}
              name="logo"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              hint={t("onboarding.logoHint")}
            />
            <Button type="submit" loading={busy}>
              {t("common.next")}
            </Button>
          </form>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <form onSubmit={createTeam} className="space-y-4" noValidate>
            <p className="text-muted">{t("onboarding.teamIntro")}</p>
            <Input
              label={t("onboarding.teamName")}
              name="name"
              placeholder={t("onboarding.teamNamePlaceholder")}
              required
              autoFocus
              error={fields.name}
            />
            <div className="grid grid-cols-2 gap-3">
              <Select label={t("onboarding.gender")} name="gender" defaultValue="men">
                {(["men", "women", "mixed"] as const).map((g) => (
                  <option key={g} value={g}>
                    {t(`genders.${g}`)}
                  </option>
                ))}
              </Select>
              <Input label={`${t("onboarding.league")} (${t("common.optional")})`} name="league" />
            </div>
            <Checkbox name="is_youth" label={t("onboarding.youth")} />
            <Button type="submit" loading={busy}>
              {t("common.next")}
            </Button>
          </form>
        </Card>
      )}

      {step === 2 && org && team?.current_season && (
        <div className="space-y-4">
          <p className="text-muted">{t("onboarding.rosterIntro")}</p>
          <RosterEditor orgId={org.id} teamId={team.id} seasonId={team.current_season.id} canEdit layout="inline" />
          <Button onClick={() => setStep(3)}>{t("common.next")}</Button>
        </div>
      )}

      {step === 3 && org && team && (
        <Card className="space-y-4">
          <p className="text-muted">{t("onboarding.inviteIntro")}</p>
          <InviteForm orgId={org.id} teams={[{ id: team.id, name: team.name }]} isAdmin />
          <Button
            onClick={() => {
              router.push(`/app/${org.id}/teams/${team.id}`);
              router.refresh();
            }}
          >
            {t("onboarding.finish")}
          </Button>
        </Card>
      )}
    </div>
  );
}
