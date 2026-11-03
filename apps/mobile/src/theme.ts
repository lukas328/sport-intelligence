import { useColorScheme } from "react-native";

/** Same tokens as the web app (globals.css), light and dark. */
const light = {
  background: "#ffffff",
  foreground: "#0f172a",
  muted: "#64748b",
  surface: "#f8fafc",
  border: "#e2e8f0",
  accent: "#0b6bcb",
  accentContrast: "#ffffff",
  ok: "#15803d",
  error: "#b91c1c",
};
const dark: typeof light = {
  background: "#0b1120",
  foreground: "#e2e8f0",
  muted: "#94a3b8",
  surface: "#111827",
  border: "#1f2937",
  accent: "#60a5fa",
  accentContrast: "#0b1120",
  ok: "#4ade80",
  error: "#f87171",
};
export type Theme = typeof light;

export function useTheme(): Theme {
  return useColorScheme() === "dark" ? dark : light;
}
