import { CalendarDays, Clapperboard, Dumbbell, Film, House, Users, type LucideIcon } from "lucide-react";
import type { Dest } from "@/lib/nav-model";

export const DEST_ICON: Record<Dest, LucideIcon> = {
  today: House,
  matches: Clapperboard,
  team: Users,
  training: Dumbbell,
  scenes: Film,
  dates: CalendarDays,
};
