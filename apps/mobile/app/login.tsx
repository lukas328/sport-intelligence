import { useRouter } from "expo-router";
import { useState } from "react";
import { Image, StyleSheet, TextInput, useColorScheme } from "react-native";
import { useSession } from "@/session";
import { useTheme } from "@/theme";
import { Body, Button, Screen, Title } from "@/ui";

export default function Login() {
  const { signIn, t } = useSession();
  const c = useTheme();
  // outside the app the mark is two-coloured (docs/design/brand2/taktik/README.md)
  const dark = useColorScheme() === "dark";
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = [styles.input, { borderColor: c.border, color: c.foreground, backgroundColor: c.background }];
  const submit = async () => {
    setBusy(true);
    const r = await signIn(email.trim(), password);
    setBusy(false);
    if (r === "ok") router.replace("/feed");
    else setMessage(r === "totp" ? t("totpNeeded") : t("signInFailed"));
  };
  return (
    <Screen>
      <Image source={dark ? require("../assets/zeichen-dunkel.png") : require("../assets/zeichen.png")} style={styles.mark} accessibilityIgnoresInvertColors />
      <Title>{t("appName")}</Title>
      <TextInput accessibilityLabel={t("email")} placeholder={t("email")} placeholderTextColor={c.muted} autoCapitalize="none" autoComplete="email" keyboardType="email-address" value={email} onChangeText={setEmail} style={input} />
      <TextInput accessibilityLabel={t("password")} placeholder={t("password")} placeholderTextColor={c.muted} secureTextEntry autoComplete="password" value={password} onChangeText={setPassword} style={input} />
      {message && <Body>{message}</Body>}
      <Button label={t("signIn")} onPress={() => void submit()} disabled={busy || !email || !password} />
    </Screen>
  );
}

const styles = StyleSheet.create({ mark: { width: 72, height: 72 }, input: { borderWidth: 1, borderRadius: 10, minHeight: 48, paddingHorizontal: 12, fontSize: 16 } });
