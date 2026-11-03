import { useLocalSearchParams } from "expo-router";
import { View } from "react-native";
import { useSession } from "@/session";
import { Body, Button, Screen } from "@/ui";

/** Phone as remote for the video session (from the presenter's QR code). */
export default function Remote() {
  const { presentationId, key } = useLocalSearchParams<{ presentationId: string; key?: string }>();
  const { api, orgId, t } = useSession();
  const send = (action: "next" | "prev" | "play" | "pause") =>
    void api.POST("/v1/orgs/{org_id}/presentations/{pres_id}/remote/command", {
      params: { path: { org_id: orgId!, pres_id: presentationId } },
      body: { key: key ?? "", action },
    });
  if (!key) return <Screen><Body>{t("error")}</Body></Screen>;
  return (
    <Screen>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <View style={{ flex: 1 }}><Button big kind="secondary" label={t("previous")} onPress={() => send("prev")} /></View>
        <View style={{ flex: 1 }}><Button big label={t("next")} onPress={() => send("next")} /></View>
      </View>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <View style={{ flex: 1 }}><Button kind="secondary" label="▶" onPress={() => send("play")} /></View>
        <View style={{ flex: 1 }}><Button kind="secondary" label="❚❚" onPress={() => send("pause")} /></View>
      </View>
    </Screen>
  );
}
