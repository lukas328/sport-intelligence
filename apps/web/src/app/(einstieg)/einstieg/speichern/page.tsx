import { Suspense } from "react";
import { SaveTeam } from "./save-team";

/** After the sign-in link: the team is taken over (or made from its name) and the coach lands on Spiele. */
export default function SavePage() {
  return (
    <Suspense>
      <SaveTeam />
    </Suspense>
  );
}
