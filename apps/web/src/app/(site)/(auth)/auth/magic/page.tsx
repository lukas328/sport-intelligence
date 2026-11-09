import { Suspense } from "react";
import { ConsumeMagicLink } from "./consume";

export default function MagicPage() {
  return (
    <Suspense>
      <ConsumeMagicLink />
    </Suspense>
  );
}
