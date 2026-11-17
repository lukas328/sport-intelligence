import { HallCamera } from "@/components/figures";

/** The hall from above for the filming page and «So funktioniert es»: the same drawing as the guide. */
export function HallPlan({
  label,
  camera,
  field,
  corner,
  framed = true,
  bare = false,
  aspect,
}: {
  label: string;
  camera: string;
  field: string;
  corner?: string;
  framed?: boolean;
  /** without the words in the drawing, at the aspect of the pictures next to it */
  bare?: boolean;
  aspect?: number;
}) {
  return <HallCamera label={label} camera={camera} field={field} corner={corner} framed={framed} bare={bare} aspect={aspect} />;
}
