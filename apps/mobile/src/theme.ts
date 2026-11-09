import { useColorScheme } from "react-native";

/** Same tokens as the web app (globals.css), light and dark. */
const light = {
  background: "#f7f7f4",
  raised: "#ffffff",
  foreground: "#121411",
  muted: "#5f635b",
  surface: "#f2f2ee",
  border: "#e3e3dd",
  accent: "#c93a0b",
  accentContrast: "#ffffff",
  ok: "#1e7b3a",
  error: "#b42318",
};
const dark: typeof light = {
  background: "#0d0e0c",
  raised: "#161815",
  foreground: "#edeee9",
  muted: "#a2a69d",
  surface: "#1f221e",
  border: "#2b2e29",
  accent: "#ff7a45",
  accentContrast: "#0d0e0c",
  ok: "#5ad17e",
  error: "#ff7b6e",
};
export type Theme = typeof light;

export function useTheme(): Theme {
  return useColorScheme() === "dark" ? dark : light;
}
