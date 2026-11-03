import { Redirect, Tabs } from "expo-router";
import { useEffect } from "react";
import { registerForPush } from "@/push";
import { useSession } from "@/session";
import { useTheme } from "@/theme";

export default function TabsLayout() {
  const { me, ready, t, api } = useSession();
  const c = useTheme();
  useEffect(() => {
    if (me) void registerForPush(api).catch(() => null);
  }, [me, api]);
  if (ready && !me) return <Redirect href="/login" />;
  return (
    <Tabs screenOptions={{ tabBarActiveTintColor: c.accent, headerTitleAlign: "left" }}>
      <Tabs.Screen name="feed" options={{ title: t("feed") }} />
      <Tabs.Screen name="schedule" options={{ title: t("schedule") }} />
      <Tabs.Screen name="assignments" options={{ title: t("assignments") }} />
      <Tabs.Screen name="more" options={{ title: t("more") }} />
    </Tabs>
  );
}
