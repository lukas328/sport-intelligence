import { createApiClient, type Schemas } from "@handball/api-client";
import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { translator } from "./i18n";

const TOKEN_KEY = "hb.session";
export const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL ?? (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? "http://localhost:3000";

type Me = Schemas["MeOut"];
type Api = ReturnType<typeof createApiClient>;

interface Session {
  ready: boolean;
  me: Me | null;
  orgId: string | null;
  api: Api;
  t: ReturnType<typeof translator>;
  signIn: (email: string, password: string) => Promise<"ok" | "failed" | "totp">;
  signOut: () => Promise<void>;
  setOrg: (id: string) => void;
}

const Ctx = createContext<Session | null>(null);

/** Sign-in with a session token kept in the device keychain and sent as bearer token. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const token = useRef<string | undefined>(undefined);
  const [ready, setReady] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [orgId, setOrg] = useState<string | null>(null);
  const api = useMemo(() => createApiClient(API_URL, { bearerToken: () => token.current }), []);

  const loadMe = useCallback(async () => {
    const r = await api.GET("/v1/me");
    setMe(r.data ?? null);
    setOrg((current) => current ?? r.data?.organizations[0]?.id ?? null);
    return r.data ?? null;
  }, [api]);

  useEffect(() => {
    void (async () => {
      token.current = (await SecureStore.getItemAsync(TOKEN_KEY)) ?? undefined;
      if (token.current) await loadMe();
      setReady(true);
    })();
  }, [loadMe]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const r = await api.POST("/v1/auth/login", { body: { email, password }, headers: { "x-client": "native" } });
      if (!r.data?.token) return "failed" as const;
      if (r.data.status === "totp_required") return "totp" as const;
      token.current = r.data.token;
      await SecureStore.setItemAsync(TOKEN_KEY, r.data.token);
      await loadMe();
      return "ok" as const;
    },
    [api, loadMe],
  );

  const signOut = useCallback(async () => {
    await api.POST("/v1/auth/logout");
    token.current = undefined;
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setMe(null);
    setOrg(null);
  }, [api]);

  const value = useMemo<Session>(
    () => ({ ready, me, orgId, api, t: translator(me?.locale), signIn, signOut, setOrg }),
    [ready, me, orgId, api, signIn, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error("SessionProvider missing");
  return s;
}
