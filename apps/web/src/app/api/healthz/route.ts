export const dynamic = "force-dynamic";

/** Liveness probe for the web container. */
export function GET() {
  return Response.json({ status: "ok", service: "handball-web" });
}
