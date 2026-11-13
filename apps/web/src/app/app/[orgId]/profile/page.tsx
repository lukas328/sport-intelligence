import { redirect } from "next/navigation";

/** Old address of the own player profile: now part of "Ich" (SPEC section 6). */
export default async function ProfilePage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  redirect(`/app/${orgId}/me`);
}
