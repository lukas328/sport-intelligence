import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { LOCALE_COOKIE, resolveLocale } from "./config";

export default getRequestConfig(async () => {
  const store = await cookies();
  // the chosen language, else the browser's first language (UX test B06)
  const chosen = store.get(LOCALE_COOKIE)?.value;
  const browser = (await headers()).get("accept-language")?.split(",")[0]?.split(";")[0]?.trim();
  const locale = resolveLocale(chosen ?? browser);
  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
    timeZone: "Europe/Zurich",
  };
});
