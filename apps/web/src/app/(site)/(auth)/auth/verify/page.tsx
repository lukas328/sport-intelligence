import { Suspense } from "react";
import { VerifyEmail } from "./verify";

export default function VerifyPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
