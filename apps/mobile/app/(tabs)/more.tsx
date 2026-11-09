import { useRouter } from "expo-router";
import { Linking } from "react-native";
import { unregisterPush } from "@/push";
import { API_URL, useSession } from "@/session";
import { Button, Screen } from "@/ui";

export default function More() {
  const { t, signOut, api, orgId } = useSession();
  const router = useRouter();
  return (
    <Screen>
      <Button label={t("record")} onPress={() => router.push("/record")} />
      <Button kind="secondary" label={t("marks")} onPress={() => router.push("/record?mode=marks")} />
      <Button kind="secondary" label={t("notifications")} onPress={() => router.push("/notifications")} />
      {/* store rule: deletion can be started from the app; it runs in the web settings (data export first) */}
      <Button kind="secondary" label={t("deleteAccount")} onPress={() => void Linking.openURL(`${API_URL}/app/${orgId ?? ""}/settings#privacy`)} />
      <Button
        kind="secondary"
        label={t("signOut")}
        onPress={() =>
          void unregisterPush(api)
            .catch(() => null)
            .then(signOut)
            .then(() => {
            router.replace("/login");
          })
        }
      />
    </Screen>
  );
}
