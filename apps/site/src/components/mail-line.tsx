import { SUPPORT_EMAIL } from "@/lib/site";

/** A sentence with {email} in it; the address becomes a mail link. */
export function MailLine({ template }: { template: string }) {
  const [before, after = ""] = template.split("{email}");
  return (
    <>
      {before}
      <a href={`mailto:${SUPPORT_EMAIL}`} className="font-bold underline decoration-2 underline-offset-4">
        {SUPPORT_EMAIL}
      </a>
      {after}
    </>
  );
}
