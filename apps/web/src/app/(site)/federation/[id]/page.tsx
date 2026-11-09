import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api";
import { FederationView } from "./federation-view";

export const metadata: Metadata = { title: "Verband", robots: { index: false } };

export default async function FederationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { data } = await (await serverApi()).GET("/v1/federations/{federation_id}", { params: { path: { federation_id: id } } });
  if (!data) notFound();
  return <FederationView id={id} initial={data} />;
}
