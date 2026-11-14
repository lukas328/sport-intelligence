import { HallCamera } from "@/components/figures";

/** The hall from above for the filming page and «So funktioniert es»: the same drawing as the guide. */
export function HallPlan({ label, camera, field, corner }: { label: string; camera: string; field: string; corner?: string }) {
  return <HallCamera label={label} camera={camera} field={field} corner={corner} />;
}
