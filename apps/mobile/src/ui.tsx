import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "./theme";

export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  const c = useTheme();
  const body = <View style={styles.body}>{children}</View>;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.background }} edges={["left", "right", "bottom"]}>
      {scroll ? <ScrollView contentContainerStyle={{ paddingBottom: 32 }}>{body}</ScrollView> : body}
    </SafeAreaView>
  );
}

export function Title({ children }: { children: ReactNode }) {
  const c = useTheme();
  return <Text accessibilityRole="header" style={[styles.title, { color: c.foreground }]}>{children}</Text>;
}

export function Body({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  const c = useTheme();
  return <Text style={{ color: muted ? c.muted : c.foreground, fontSize: 15, lineHeight: 21 }}>{children}</Text>;
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const c = useTheme();
  return <View style={[styles.card, { borderColor: c.border, backgroundColor: c.surface }, style]}>{children}</View>;
}

export function Button({
  label,
  onPress,
  kind = "primary",
  disabled = false,
  big = false,
  color,
}: {
  label: string;
  onPress: () => void;
  kind?: "primary" | "secondary";
  disabled?: boolean;
  big?: boolean;
  color?: string;
}) {
  const c = useTheme();
  const primary = kind === "primary";
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        big && styles.big,
        {
          backgroundColor: primary ? c.accent : c.background,
          borderColor: color ?? (primary ? c.accent : c.border),
          opacity: disabled ? 0.5 : pressed ? 0.8 : 1,
        },
      ]}
    >
      <Text style={{ color: primary ? c.accentContrast : c.foreground, fontWeight: "600", fontSize: big ? 20 : 16 }}>{label}</Text>
    </Pressable>
  );
}

export function Loading() {
  return <ActivityIndicator style={{ marginTop: 32 }} />;
}

const styles = StyleSheet.create({
  body: { padding: 16, gap: 12 },
  title: { fontSize: 22, fontWeight: "700" },
  card: { borderWidth: 1, borderRadius: 12, padding: 14, gap: 8 },
  button: { minHeight: 48, borderRadius: 10, borderWidth: 2, alignItems: "center", justifyContent: "center", paddingHorizontal: 16 },
  big: { minHeight: 96 },
});
