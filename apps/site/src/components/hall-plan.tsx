import { HallCamera } from "@/components/figures";

/** The hall from above for the filming page and «So funktioniert es»: the same drawing as the guide. */
export function HallPlan({ label, camera, field, corner, framed = true }: { label: string; camera: string; field: string; corner?: string; framed?: boolean }) {
  return <HallCamera label={label} camera={camera} field={field} corner={corner} framed={framed} />;
}
