import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { NewPlaylist } from "./new-playlist";

export default async function PlaylistsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("playlists");
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [lists, team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const staff = org.data?.my_role === "org_admin" || ["coach", "analyst"].includes(team.data?.my_role ?? "");
  const items = lists.data ?? [];
  return (
    <div className="space-y-6">
      {staff && <NewPlaylist orgId={orgId} teamId={teamId} />}
      {items.length === 0 ? (
        <EmptyState title={t("empty")}>{staff && t("emptyHint")}</EmptyState>
      ) : (
        <ul className="divide-y divide-foreground/10 border-t-2 border-foreground">
          {items.map((p) => (
            <li key={p.id}>
              <Link href={`/app/${orgId}/playlists/${p.id}`} className="group flex flex-wrap items-baseline gap-x-3 py-3">
                <span className="flex-1 font-medium group-hover:underline group-hover:underline-offset-4">{p.title}</span>
                <span className="text-sm text-muted">
                  {t("items", { count: p.item_count })} · {p.shared_with_players ? t("shared") : t("notShared")}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
