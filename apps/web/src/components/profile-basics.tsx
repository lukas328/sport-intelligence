"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { LANGUAGE_NAMES, setLanguage } from "@/components/language-switch";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { locales, type Locale } from "@/i18n/config";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { useMailEnabled } from "@/lib/site-config";
import { cn } from "@/lib/utils";

type Me = Schemas["MeOut"];

/**
 * Mein Konto › Profil (A13): who you are in the app, first. Name, e-mail and language; password and
 * devices are under «Sicherheit».
 */
export function ProfileBasics({ me }: { me: Me }) {
  const t = useTranslations();
  const router = useRouter();
  const current = useLocale() as Locale;
  const mail = useMailEnabled();
  const [name, setName] = useState(me.name);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);
  const [resent, setResent] = useState(false);
  const [resendError, setResendError] = useState<ErrorKey | null>(null);

  async function saveName(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const next = name.trim();
    if (!next) return;
    setBusy(true);
    const { error: err } = await api.PATCH("/v1/me", { body: { name: next } });
    setBusy(false);
    if (err) {
      setSaved(false);
      return setError(errorKey(err));
    }
    setError(null);
    setSaved(true);
    router.refresh();
  }

  async function pickLanguage(l: Locale) {
    setLanguage(l);
    // the choice follows the person to other devices and into the e-mails
    await api.PATCH("/v1/me", { body: { locale: l } });
    router.refresh();
  }

  return (
    <section aria-labelledby="profile-title" className="space-y-6" data-testid="profile-basics">
      <h2 id="profile-title" className="sr-only">
        {t("settings.tab_profile")}
      </h2>
      <form onSubmit={saveName} className="space-y-3" aria-label={t("account.nameLabel")}>
        {error && <Alert>{t(`errors.${error}`)}</Alert>}
        <Input
          label={t("account.nameLabel")}
          name="name"
          autoComplete="name"
          value={name}
          maxLength={120}
          required
          onChange={(e) => {
            setName(e.target.value);
            setSaved(false);
          }}
        />
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" variant="secondary" loading={busy} disabled={!name.trim() || name.trim() === me.name}>
            {t("account.saveName")}
          </Button>
          {saved && (
            <span role="status" className="text-[15px] font-semibold text-ok">
              {t("account.nameSaved")}
            </span>
          )}
        </div>
      </form>

      <div className="space-y-2 border-t border-foreground/15 pt-5">
        <h3 className="font-semibold">{t("account.emailLabel")}</h3>
        <p className="m-0 text-[17px] break-all" data-testid="profile-email">
          {me.email}
        </p>
        <p className="m-0 text-sm text-muted">{t("account.emailHint")}</p>
        {!me.email_verified && mail && (
          <Alert kind="info">
            {t("account.emailUnverified")}{" "}
            {resent ? (
              t("account.resent")
            ) : (
              <button
                type="button"
                className="underline underline-offset-4"
                onClick={async () => {
                  const { error: err } = await api.POST("/v1/me/email/verify");
                  if (err) return setResendError(errorKey(err));
                  setResendError(null);
                  setResent(true);
                }}
              >
                {t("account.resend")}
              </button>
            )}
            {resendError && <span className="mt-1 block">{t(`errors.${resendError}`)}</span>}
          </Alert>
        )}
      </div>

      <div className="space-y-2 border-t border-foreground/15 pt-5">
        <h3 id="profile-language" className="font-semibold">
          {t("account.languageLabel")}
        </h3>
        <div role="group" aria-labelledby="profile-language" className="flex flex-wrap gap-2" data-testid="profile-language">
          {locales.map((l) => (
            <button
              key={l}
              type="button"
              lang={l}
              aria-pressed={l === current}
              onClick={() => void pickLanguage(l)}
              className={cn(
                "min-h-11 cursor-pointer border-2 px-4 text-[15px] font-semibold",
                l === current ? "border-ink bg-ink text-ground" : "border-ink bg-transparent text-ink hover:bg-surface",
              )}
            >
              {LANGUAGE_NAMES[l]}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
