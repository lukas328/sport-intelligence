import { parse, type Route } from "@handball/client-core";
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import type { useSession } from "./session";

type Api = ReturnType<typeof useSession>["api"];

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

/** Asks once for permission and registers the Expo push token with the API (APNs/FCM behind it). */
export async function registerForPush(api: Api): Promise<string | null> {
  if (!Device.isDevice) return null;
  const current = await Notifications.getPermissionsAsync();
  const status = current.granted ? current : await Notifications.requestPermissionsAsync();
  if (!status.granted) return null;
  const projectId = (Constants.expoConfig?.extra?.eas as { projectId?: string } | undefined)?.projectId;
  const token = (await Notifications.getExpoPushTokenAsync(projectId ? { projectId } : {})).data;
  await api.POST("/v1/me/devices", { body: { token, platform: Platform.OS === "ios" ? "ios" : "android" } });
  registered = token;
  return token;
}

let registered: string | null = null;

/** On sign-out the device stops getting pushes for this account. */
export async function unregisterPush(api: Api): Promise<void> {
  if (!registered) return;
  await api.DELETE("/v1/me/devices/{token}", { params: { path: { token: registered } } });
  registered = null;
}

/** The screen a tapped notification opens (the API sends the web link of the notification). */
export function routeOf(response: Notifications.NotificationResponse): Route {
  const data = response.notification.request.content.data as { link?: string } | undefined;
  return parse(data?.link);
}
