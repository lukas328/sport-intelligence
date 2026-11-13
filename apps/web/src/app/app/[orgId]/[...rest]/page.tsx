import { notFound } from "next/navigation";

/** An unknown address inside the app shows the 404 in the app frame (UX test B53). */
export default function UnknownInApp() {
  notFound();
}
