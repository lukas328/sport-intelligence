"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { clubStyle, DEFAULT_CLUB } from "@/lib/color";
import { PageHeader } from "@/components/ui/page-header";
import { useEffect, useState, type FormEvent } from "react";
import { ClubColourPicker } from "@/components/anlauf/club-colour-picker";
import { skipColourHint } from "@/lib/colour-hint";
import { Button, buttonClass } from "@/components/ui/button";
import { similarTeams } from "@/lib/team-names";
import { Alert, Card } from "@/components/ui/card";
import { Checkbox, Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { signupSource } from "@/lib/signup-source";
import { browserCountry, COUNTRIES, countryName } from "@/lib/country";
import { OfficialTeamSearch } from "./team-search";
import { CLAIM_KEY, CONFIRM_COOKIE, forgetClaim } from "./claim-storage";
import { ConfirmTeam } from "./confirm-team";
import type { OfficialTeam } from "@/lib/official-teams";
import { errorKey, fieldErrors, type ErrorKey } from "@/lib/errors";

type Org = Schemas["OrgOut"];
type Team = Schemas["TeamOut"];
// by hand: the club's name, its colour (one tap or «Später», decision E8), then the team; the
// roster and the invitations come later from the team page and the club (UX test B27)
const STEPS = ["stepClub", "stepColour", "stepTeam"] as const;
const COLOUR_STEP = 1;
const TEAM_STEP = 2;
// with the official data the onboarding is two steps: find the team, confirm it (SPEC 7.12)
const OFFICIAL_STEPS = ["stepFind", "stepConfirm"] as const;

export function OnboardingWizard({ existingOrg, resume = false, waiting = [] }: { existingOrg?: Org; resume?: boolean; /** clubs whose admins have not answered an access request yet */ waiting?: string[] }) {
  const t = useTranslations();
  const locale = useLocale();
  // the browser's country after mount (the server does not know it): the select starts there
  const [guess, setGuess] = useState("CH");
  useEffect(() => setGuess(browserCountry()), []);
  const router = useRouter();
  // a club made here before: its colour if it has none yet, else the team
  const [step, setStep] = useState(existingOrg ? (existingOrg.color_chosen ? TEAM_STEP : COLOUR_STEP) : 0);
  const [org, setOrg] = useState<Org | undefined>(existingOrg);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  // the club colour as it is being picked (null: none yet): the welcome band shows it right away,
  // and the neutral slate of a club without a colour until then
  const [chosen, setChosen] = useState<string | null>(existingOrg?.color_chosen ? existingOrg.primary_color : null);
  const colour = chosen ?? DEFAULT_CLUB;
  const [name, setName] = useState(existingOrg?.name ?? "");
  // a new coach first looks for the team in the official data; a club by hand on request
  const [manual, setManual] = useState(false);
  // a team taken over from the official data: club and team are there, step 2 confirms them
  const [claimed, setClaimed] = useState<{ out: Schemas["ClaimOut"]; team: OfficialTeam } | null>(null);
  useEffect(() => {
    if (!resume) return;
    try {
      const saved = JSON.parse(window.sessionStorage.getItem(CLAIM_KEY) ?? "null") as { out: Schemas["ClaimOut"]; team: OfficialTeam; club: string } | null;
      if (saved) {
        setName(saved.club);
        setClaimed({ out: saved.out, team: saved.team });
        return;
      }
    } catch {
      /* storage unavailable */
    }
    // nothing to resume from in this browser: on into the app
    forgetClaim();
    router.replace("/app");
  }, [resume, router]);
  const official = step === 0 && !manual;
  const steps: readonly string[] = official ? OFFICIAL_STEPS : STEPS;
  const shownStep = official ? (claimed ? 1 : 0) : step;
  // a player who asked to join a team has no club steps ahead
  const [joined, setJoined] = useState(false);
  // teams of the club with a similar name, and whether the coach wants a new one anyway (K17)
  const [twins, setTwins] = useState<{ id: string; name: string }[]>([]);
  const [twinOk, setTwinOk] = useState(false);

  async function createOrg(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    const { data, error } = await api.POST("/v1/orgs", {
      // no colour yet: the next step asks for it
      body: { name: String(f.get("name")), country: String(f.get("country")), source: signupSource() },
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
    setStep(COLOUR_STEP);
  }

  async function saveColour(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!org) return;
    if (!chosen) return skipColour();
    setBusy(true);
    setError(null);
    const { data, error } = await api.PATCH("/v1/orgs/{org_id}", { params: { path: { org_id: org.id } }, body: { primary_color: chosen } });
    setBusy(false);
    if (error || !data) return setError(errorKey(error));
    setOrg(data);
    setStep(TEAM_STEP);
  }

  function skipColour() {
    // «Später»: the club shows the neutral slate; the hint on the club's pages waits for the next visit
    if (org) skipColourHint(org.id);
    setChosen(null);
    setError(null);
    setStep(TEAM_STEP);
  }

  async function createTeam(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!org) return;
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    const league = String(f.get("league") ?? "").trim();
    // a team typed by hand can exist twice: say so before making a second one (K17)
    if (!twinOk) {
      const existing = (await api.GET("/v1/orgs/{org_id}/teams", { params: { path: { org_id: org.id } } })).data ?? [];
      const same = similarTeams(String(f.get("name") ?? ""), existing);
      if (same.length > 0) {
        setBusy(false);
        return setTwins(same.map((x) => ({ id: x.id, name: x.name })));
      }
    }
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
    // on to Spiele: the next steps stand there (K17)
    router.push(`/app/${org.id}/teams/${data.id}/matches`);
    router.refresh();
  }

  return (
    <div className={claimed ? "space-y-8" : "mx-auto max-w-2xl space-y-8"}>
      {/* the Seitenkopf takes the club colour as it is picked: the Keil shows it right away */}
      <div className="club" style={clubStyle(colour) as CSSProperties}>
        <PageHeader eyebrow={!joined ? t("onboarding.progress", { step: shownStep + 1, total: steps.length }) : undefined} title={claimed ? t("onboarding.confirmTitle") : name.trim() || t("onboarding.title")} />
        {!joined && !claimed && (
          <ol className="-mt-2 flex max-w-md gap-2" aria-label={t("onboarding.progress", { step: shownStep + 1, total: steps.length })}>
            {steps.map((s, i) => (
              <li key={s} aria-current={i === shownStep ? "step" : undefined} className={`flex-1 space-y-1.5 text-[15px] ${i <= shownStep ? "font-bold text-ink" : "text-ink-2"}`}>
                <span aria-hidden className={`block h-1.5 ${i <= shownStep ? "bg-ink" : "bg-rule"}`} />
                {t(`onboarding.${s}` as "onboarding.stepClub")}
              </li>
            ))}
          </ol>
        )}
      </div>
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {/* asked to join a team that is already in the app: it waits for its admins (K17) */}
      {waiting.length > 0 && !claimed && (
        <section className="max-w-[65ch] border-l-4 border-attn bg-surface px-4 py-3" data-testid="onboarding-waiting">
          <p className="m-0 font-bold">{t("onboarding.waitingTitle", { club: waiting.join(", ") })}</p>
          <p className="mt-1 mb-0 text-[15px]">{t("onboarding.waitingText")}</p>
        </section>
      )}

      {official && !claimed && <OfficialTeamSearch onManual={() => setManual(true)} onClaimed={(club, out, team) => {
            setName(club);
            setJoined(false);
            setClaimed({ out, team });
            try {
              window.sessionStorage.setItem(CLAIM_KEY, JSON.stringify({ out, team, club }));
            } catch {
              /* storage unavailable */
            }
            if (out.organization_id) document.cookie = `${CONFIRM_COOKIE}=${out.organization_id}; path=/; max-age=3600; samesite=lax`;
          }} onJoinSent={() => setJoined(true)} />}
      {official && claimed?.out.organization_id && claimed.out.team_id && (
        <ConfirmTeam
          claimed={claimed.out}
          teamName={claimed.team.name}
          league={claimed.team.league || claimed.team.group_name || ""}
          chosen={chosen}
          onChoose={setChosen}
          onNotMine={() => (forgetClaim(), setClaimed(null), setName(""))}
        />
      )}

      {step === 0 && manual && (
        <Card>
          <form onSubmit={createOrg} className="space-y-4" noValidate>
            <p className="text-muted">{t("onboarding.clubIntro")}</p>
            <Input label={t("onboarding.clubName")} name="name" required autoFocus error={fields.name} value={name} onChange={(e) => setName(e.target.value)} />
            {/* the rest can wait: country, crest */}
            <details className="group">
              <summary className="min-h-11 cursor-pointer content-center text-[15px] font-bold underline decoration-[1.5px] underline-offset-4">{t("onboarding.moreClub")}</summary>
              <div className="space-y-4 pt-3">
                {/* a guess from the browser (time zone, language): it sets the billing currency */}
                <Select label={t("onboarding.country")} name="country" key={guess} defaultValue={guess}>
                  {COUNTRIES.map((c) => (
                    <option key={c} value={c}>
                      {countryName(c, locale)}
                    </option>
                  ))}
                </Select>
                <Input
                  label={`${t("onboarding.logo")} (${t("common.optional")})`}
                  name="logo"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  hint={t("onboarding.logoHint")}
                />
              </div>
            </details>
            <Button type="submit" loading={busy}>
              {t("common.next")}
            </Button>
          </form>
        </Card>
      )}

      {step === COLOUR_STEP && !claimed && (
        <Card>
          <form onSubmit={saveColour} className="space-y-5" noValidate data-testid="colour-step">
            <ClubColourPicker value={chosen} onChange={setChosen} legend={t("onboarding.colourTitle")} note={t("onboarding.colourNote")} />
            {/* a colour outside the eight (a yellow or white club): the club page has more */}
            <details>
              <summary className="min-h-11 cursor-pointer content-center text-[15px] font-bold underline decoration-[1.5px] underline-offset-4">{t("onboarding.ownColour")}</summary>
              <div className="pt-3">
                <Input label={t("onboarding.primaryColor")} type="color" value={colour} onChange={(e) => setChosen(e.target.value)} className="h-11 w-24 p-1" />
              </div>
            </details>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
              <Button type="submit" loading={busy} data-testid="colour-next">
                {t("common.next")}
              </Button>
              <Button type="button" variant="secondary" onClick={skipColour} disabled={busy} data-testid="colour-later">
                {t("onboarding.colourLater")}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {step === TEAM_STEP && (
        <Card>
          <form onSubmit={createTeam} className="space-y-4" noValidate>
            <p className="text-muted">{t("onboarding.teamIntro")}</p>
            <p className="text-[15px] text-ink-2">{t("onboarding.rosterLater")}</p>
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
            {twins.length > 0 && org && (
              <div className="space-y-3 border-l-4 border-attn bg-surface px-4 py-3" role="alert" data-testid="team-twin">
                <p className="m-0 font-bold">{t("onboarding.twinTitle", { names: twins.map((x) => x.name).join(", ") })}</p>
                <p className="m-0 text-[15px]">{t("onboarding.twinText")}</p>
                <div className="flex flex-wrap gap-3">
                  <a href={`/app/${org.id}/teams/${twins[0]!.id}`} className={buttonClass("primary", "sm")}>
                    {t("onboarding.twinOpen", { name: twins[0]!.name })}
                  </a>
                  <Button size="sm" variant="secondary" onClick={() => (setTwinOk(true), setTwins([]))} data-testid="team-twin-anyway">
                    {t("onboarding.twinAnyway")}
                  </Button>
                </div>
              </div>
            )}
            <Button type="submit" loading={busy}>
              {twinOk ? t("onboarding.twinCreate") : t("onboarding.finish")}
            </Button>
          </form>
        </Card>
      )}

    </div>
  );
}
