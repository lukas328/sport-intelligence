/** The facts of «Fakten auf einen Blick», filled in once for the page and for llms.txt. */
import plans from "@handball/plans";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { fileVars } from "@/lib/files";
import { SUPPORT_EMAIL } from "@/lib/site";

export function factRows(locale: Locale): { k: string; v: string }[] {
  const team = plans.plans.find((p) => p.plan === "team")!;
  const club = plans.plans.find((p) => p.plan === "club")!;
  const m = messages(locale);
  const vars = { team: team.price_chf_month, club: club.price_chf_month, clubTeams: club.teams, email: SUPPORT_EMAIL, ...fileVars(m) };
  return m.facts.rows.map((r) => ({ k: r.k, v: fmt(r.v, vars) }));
}
