import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";
import deCH from "../../../messages/de-CH.json";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";
import { goalWords, matchMinute, ogDescription, ogImageUrl, ogTitle, publicOrigin, shareMetadata, type SharePreview } from "./meta";
import { blockedReason, daysLeft, isPreviewBot, liveLink, reasonFromProblem } from "./policy";
import { chatMessage, chatText, SHARE_KINDS, shareUrl, whatsappHref, type T } from "./text";

const tr = (messages: object, locale: string): T => createTranslator({ locale, messages: messages as typeof deCH }) as unknown as T;
const t = tr(deCH, "de-CH");

const base: SharePreview = {
  kind: "scene",
  title: "TV Farnwil - SG Kalvenegg",
  club: "TV Farnwil",
  team: "Herren 1",
  scenes: 1,
  duration_s: 8,
  kit: { a: "#c8102e", b: "#ffffff" },
  expires_at: "2026-12-16T12:00:00Z",
};

describe("chat text", () => {
  it("is one short sentence per kind, with at most one emoji, and the link on its own line", () => {
    const cases = [
      chatText(t, { kind: "scene", title: "Gegenstoss 3:2" }),
      chatText(t, { kind: "collection", title: "Rückzug", scenes: 5 }),
      chatText(t, { kind: "highlight", title: "Highlights", team: "TV Farnwil", opponent: "SG Kalvenegg", score: [28, 24] }),
      chatText(t, { kind: "match", title: "TV Farnwil - SG Kalvenegg", team: "TV Farnwil", opponent: "SG Kalvenegg", score: [28, 24] }),
      chatText(t, { kind: "play", title: "Kreuzen" }),
    ];
    expect(cases).toEqual([
      "▶️ Schaut euch diese Szene an: Gegenstoss 3:2",
      "▶️ Rückzug: 5 Szenen. Schaut sie euch bis zum nächsten Training an.",
      "🔥 Unsere Highlights gegen SG Kalvenegg (28:24)",
      "TV Farnwil 28:24 SG Kalvenegg: der Spielbericht mit allen Zahlen.",
      "📋 Spielzug «Kreuzen»: bitte vor dem Training anschauen.",
    ]);
    for (const c of cases) {
      expect(c.length).toBeLessThan(110);
      expect((c.match(/\p{Extended_Pictographic}/gu) ?? []).length).toBeLessThanOrEqual(1);
      expect(c).not.toMatch(/[–—ß]/);
    }
    expect(chatMessage(t, { kind: "play", title: "Kreuzen" }, "https://app.example/s/abc")).toBe("📋 Spielzug «Kreuzen»: bitte vor dem Training anschauen.\nhttps://app.example/s/abc");
  });

  it("falls back without result and exists in every language for every kind", () => {
    expect(chatText(t, { kind: "match", title: "TV Farnwil - SG Kalvenegg" })).toBe("Spielbericht TV Farnwil - SG Kalvenegg: alle Zahlen im Link.");
    expect(chatText(t, { kind: "highlight", title: "Highlights", team: "Herren 1" })).toBe("🔥 Highlights von Herren 1");
    for (const [m, l] of [[fr, "fr"], [en, "en"]] as const) {
      const tt = tr(m, l);
      for (const kind of SHARE_KINDS) expect(chatText(tt, { kind, title: "X", scenes: 2, team: "A", opponent: "B", score: [1, 2] })).not.toMatch(/share\.|\{/);
    }
  });

  it("builds the WhatsApp link with the whole message", () => {
    const href = whatsappHref("▶️ Szene: Tor\nhttps://app.example/s/abc");
    expect(href.startsWith("https://wa.me/?text=")).toBe(true);
    expect(decodeURIComponent(href.split("text=")[1]!)).toBe("▶️ Szene: Tor\nhttps://app.example/s/abc");
    expect(shareUrl("https://app.example/", "tok")).toBe("https://app.example/s/tok");
  });
});

describe("open graph", () => {
  it("names the minute and the goal of a scene", () => {
    expect(matchMinute(22.97)).toBe(23);
    expect(matchMinute(0)).toBe(1);
    expect(matchMinute(null)).toBeNull();
    const scene = { ...base, goal: { team: "own" as const, zone: "la", minute: 22.5 }, opponent: "SG Kalvenegg" };
    expect(ogTitle(t, scene)).toBe("Szene 23. Min: Tor von aussen links");
    expect(goalWords(t, { team: "opp", zone: "gs" })).toBe("Gegentor nach Gegenstoss");
    expect(ogTitle(t, { ...base, opponent: "SG Kalvenegg" })).toBe("Szene gegen SG Kalvenegg");
    expect(ogTitle(t, { ...base, title: "Gegenstoss 3:2" })).toBe("Szene: Gegenstoss 3:2");
    expect(ogDescription(t, scene)).toBe("TV Farnwil Herren 1 · gegen SG Kalvenegg · ohne Konto ansehen");
  });

  it("puts the result in the title of a match and the count in a collection", () => {
    const match = { ...base, kind: "match", title: "Herren 1 - SG Kalvenegg", opponent: "SG Kalvenegg", score: [28, 24], halftime: [14, 11], kickoff_at: "2026-11-15T18:00:00Z" };
    expect(ogTitle(t, match)).toBe("TV Farnwil Herren 1 28:24 SG Kalvenegg");
    expect(ogDescription(t, match)).toBe("TV Farnwil Herren 1 · 15. November 2026 · Halbzeit 14:11 · ohne Konto ansehen");
    expect(ogTitle(t, { ...base, kind: "collection", title: "Rückzug", scenes: 5, duration_s: 130 })).toBe("Rückzug: 5 Szenen");
    expect(ogDescription(t, { ...base, kind: "collection", title: "Rückzug", scenes: 5, duration_s: 130 })).toBe("TV Farnwil Herren 1 · 2 min · ohne Konto ansehen");
    expect(ogTitle(t, { ...base, kind: "play", title: "Kreuzen" })).toBe("Spielzug: Kreuzen");
    expect(ogTitle(t, { ...base, kind: "highlight", title: "Highlights", opponent: "SG Kalvenegg", score: [28, 24] })).toBe("Highlights: TV Farnwil Herren 1 28:24 SG Kalvenegg");
  });

  it("keeps the description to one line", () => {
    const long = { ...base, club: "Handballclub mit einem sehr langen Vereinsnamen", team: "Junioren U19 Elite Inter", opponent: "Ein Gegner mit langem Namen aus dem Kanton" };
    expect(ogDescription(t, long).length).toBeLessThanOrEqual(90);
  });

  it("gives absolute URLs, the picture size, a video for a reel and never indexes", () => {
    const md = shareMetadata(t, { ...base, kind: "highlight", title: "Highlights", reel: { format: "16x9" } }, { origin: "https://app.handball-intelligence.com", token: "tok" });
    expect(md.robots).toEqual({ index: false, follow: false });
    const og = md.openGraph as { images: { url: string; width: number; height: number }[]; videos: { url: string; type: string }[]; url: string; siteName: string; type: string };
    expect(og.url).toBe("https://app.handball-intelligence.com/s/tok");
    expect(og.images[0]).toMatchObject({ url: ogImageUrl("https://app.handball-intelligence.com", "tok"), width: 1200, height: 630 });
    expect(og.images[0]!.url).toMatch(/^https:\/\/app\.handball-intelligence\.com\/s\/tok\/og\?v=\d+$/);
    expect(og.videos[0]).toMatchObject({ url: "https://app.handball-intelligence.com/v1/share/tok/reel.mp4", type: "video/mp4" });
    expect(og.siteName).toBe("TV Farnwil");
    expect(og.type).toBe("video.other");
    expect((md.twitter as { card: string }).card).toBe("summary_large_image");
    const plain = shareMetadata(t, base, { origin: "https://x.ch", token: "t2" });
    expect((plain.openGraph as { videos?: unknown }).videos).toBeUndefined();
  });

  it("finds the public origin behind the ingress", () => {
    const h = (o: Record<string, string>) => ({ get: (k: string) => o[k] ?? null });
    expect(publicOrigin(h({ host: "app.handball-intelligence.com", "x-forwarded-proto": "https" }))).toBe("https://app.handball-intelligence.com");
    expect(publicOrigin(h({ host: "internal:3000", "x-forwarded-host": "app.example.ch" }))).toBe("https://app.example.ch");
    expect(publicOrigin(h({ host: "localhost:3104" }))).toBe("http://localhost:3104");
    expect(publicOrigin(h({ host: "x" }), "https://configured.ch/")).toBe("https://configured.ch");
  });
});

describe("share policy", () => {
  const youth = { youth: true, default_days: 30, kinds: { play: null, match: "youth-protection", scene: "youth-protection" } };
  it("explains the youth rule and other refusals", () => {
    expect(blockedReason(youth, "play")).toBeNull();
    expect(blockedReason(youth, "match")).toBe("youth-protection");
    expect(blockedReason(null, "match")).toBeNull();
    expect(blockedReason({ youth: false, default_days: 30, kinds: { match: "something-new" } }, "match")).toBeNull();
    expect(reasonFromProblem({ type: "https://handball-intelligence.com/problems/consent-missing" })).toBe("consent-missing");
    expect(reasonFromProblem({ type: "https://x/problems/org-unverified" })).toBe("unverified");
    expect(reasonFromProblem({ type: "https://x/problems/plan-required" })).toBe("plan");
    expect(reasonFromProblem({ type: "https://x/problems/not-found" })).toBeNull();
    expect(reasonFromProblem(undefined)).toBeNull();
  });

  it("offers the same link again instead of a second one", () => {
    const now = Date.parse("2026-11-16T12:00:00Z");
    const links = [
      { kind: "scene", target_id: "a", revoked_at: "2026-11-10T00:00:00Z", expires_at: "2026-12-01T00:00:00Z", token: "old" },
      { kind: "scene", target_id: "a", revoked_at: null, expires_at: "2026-11-15T00:00:00Z", token: "expired" },
      { kind: "scene", target_id: "a", revoked_at: null, expires_at: "2026-12-01T00:00:00Z", token: null },
      { kind: "scene", target_id: "a", revoked_at: null, expires_at: "2026-12-01T00:00:00Z", token: "live" },
    ];
    expect(liveLink(links, "scene", "a", now)?.token).toBe("live");
    expect(liveLink(links, "collection", "a", now)).toBeNull();
    expect(daysLeft("2026-11-17T12:00:00Z", now)).toBe(1);
  });

  it("does not count the link previews of the chats", () => {
    for (const ua of ["WhatsApp/2.23.20.0 A", "WhatsApp/2", "facebookexternalhit/1.1 Facebot Twitterbot/1.0", "TelegramBot (like TwitterBot)", "Slackbot-LinkExpanding 1.0", "Mozilla/5.0 (compatible; Discordbot/2.0)"]) expect(isPreviewBot(ua)).toBe(true);
    for (const ua of ["Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1", "Mozilla/5.0 (Linux; Android 14; CUBOT P80) Chrome/130 Mobile Safari/537.36", null])
      expect(isPreviewBot(ua)).toBe(false);
  });
});
