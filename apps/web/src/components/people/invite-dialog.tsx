"use client";

import { UserPlus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DialogContent, DialogRoot } from "@/components/ui/dialog";
import type { PersonRole } from "@/lib/roles";
import { InviteForm } from "./invite-form";

/** «Einladen» right where the team is (Team page, next steps): the invite form in a dialog. */
export function InviteDialog({
  orgId,
  team,
  isAdmin,
  role = "co_trainer",
  label,
  variant = "secondary",
  open: controlled,
  onOpenChange,
}: {
  orgId: string;
  team: { id: string; name: string; team_features?: boolean };
  isAdmin: boolean;
  role?: PersonRole;
  label?: string;
  variant?: "primary" | "secondary";
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const t = useTranslations("people");
  const [own, setOwn] = useState(false);
  const open = controlled ?? own;
  const setOpen = onOpenChange ?? setOwn;
  return (
    <>
      {controlled === undefined && (
        <Button variant={variant} size="sm" onClick={() => setOpen(true)} data-testid="invite-open">
          <UserPlus aria-hidden />
          {label ?? t("invite")}
        </Button>
      )}
      <DialogRoot open={open} onOpenChange={setOpen}>
        <DialogContent title={t("inviteTitle", { team: team.name })} wide>
          <InviteForm orgId={orgId} teams={[team]} isAdmin={isAdmin} initialRole={role} initialTeam={team.id} />
        </DialogContent>
      </DialogRoot>
    </>
  );
}
