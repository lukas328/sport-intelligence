import { getLocale, getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { matchCardPicture } from "@/lib/share/og-image";
import type { T } from "@/lib/share/text";

export const runtime = "nodejs";

/**
 * Die Spielkarte (K20): result and the three things of a match as a square PNG for the team chat,
 * for whoever may read the match. No names and no jersey numbers on it, so youth teams may post
 * it too. `?download=1` asks the browser to save it.
 */
export async function GET(req: Request, { params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  const api = await serverApi();
  const path = { org_id: orgId, match_id: matchId };
  const [match, graphics, org] = await Promise.all([
    api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path } }),
    api.GET("/v1/orgs/{org_id}/matches/{match_id}/graphics", { params: { path } }),
    api.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const m = match.data;
  if (!m || m.score_own == null || m.score_opponent == null) return new Response(null, { status: m ? 409 : 404 });
  const team = await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: m.team_id } } });
  const t = (await getTranslations()) as unknown as T;
  const res = await matchCardPicture(
    {
      club: org.data?.name ?? "",
      team: team.data?.name ?? "",
      opponent: m.opponent?.name ?? null,
      score: [m.score_own, m.score_opponent],
      halftime: m.halftime_own != null && m.halftime_opponent != null ? [m.halftime_own, m.halftime_opponent] : null,
      kickoffAt: m.kickoff_at,
      kit: { a: org.data?.primary_color, b: org.data?.secondary_color },
      oppKit: m.opponent?.primary_color ?? null,
      goals: graphics.data?.goals.map((g) => ({ team: g.team, zone: g.zone ?? null })) ?? [],
    },
    t,
    await getLocale(),
  );
  if (new URL(req.url).searchParams.get("download")) {
    const slug = `${t("share.card.file")}-${m.opponent?.name ?? ""}-${m.score_own}-${m.score_opponent}`.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w]+/g, "-").replace(/^-|-$/g, "");
    res.headers.set("content-disposition", `attachment; filename="${slug}.png"`);
  }
  return res;
}
