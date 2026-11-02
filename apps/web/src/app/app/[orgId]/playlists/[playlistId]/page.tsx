import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api";
import { PlaylistView } from "./playlist-view";

export default async function PlaylistPage({ params }: { params: Promise<{ orgId: string; playlistId: string }> }) {
  const { orgId, playlistId } = await params;
  const client = await serverApi();
  const { data: playlist } = await client.GET("/v1/orgs/{org_id}/playlists/{playlist_id}", {
    params: { path: { org_id: orgId, playlist_id: playlistId } },
  });
  if (!playlist) notFound();
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: playlist.team_id } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const staff = org.data?.my_role === "org_admin" || ["coach", "analyst"].includes(team.data?.my_role ?? "");
  return <PlaylistView orgId={orgId} initial={playlist} staff={staff} />;
}
