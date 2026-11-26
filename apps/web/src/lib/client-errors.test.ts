import { describe, expect, it } from "vitest";
import { deviceOf, domHint, isHydration, markOf, maskRoute, maskText, MAX_PER_SESSION, reactCode, reportOf, takeSlot } from "./client-errors";

const ID = "4a9f2d24-f32c-42b7-9d1b-9a86a6c6ffd5";

describe("client error reports carry nothing personal", () => {
  it("masks ids, e-mail addresses and URL queries", () => {
    expect(maskText(`no ${ID} for coach@hc-test.ch at https://a.test/x?token=1#f`)).toBe("no :id for [email] at https://a.test/x");
    expect(maskRoute(`/app/${ID}/matches/${ID}/check?shots=1`)).toBe("/app/:id/matches/:id/check");
    expect(maskRoute("/app/x/teams/12/players#k")).toBe("/app/x/teams/:n/players");
  });

  it("reads React's error number from a minified message", () => {
    expect(reactCode("Minified React error #418; visit https://react.dev/errors/418?args[]=HTML")).toBe(418);
    expect(reactCode("TypeError: x is undefined")).toBeNull();
  });

  it("builds the report: a hydration mismatch is a React error; extensions and empty ones are dropped", () => {
    const r = reportOf(new Error(`Minified React error #418 on ${ID}`), "error", `/app/${ID}/matches/${ID}`, "phone", "1df1ea0");
    expect(r).toMatchObject({ kind: "react", code: 418, route: "/app/:id/matches/:id", build: "1df1ea0", device: "phone" });
    expect(r!.message).not.toContain(ID);
    const ext = new Error("boom");
    ext.stack = "Error: boom\n at chrome-extension://abc/x.js:1:1";
    expect(reportOf(ext, "error", "/", "desktop", null)).toBeNull();
    expect(reportOf(undefined, "rejection", "/", "desktop", null)).toBeNull();
    expect(reportOf("plain text", "rejection", "/", "tablet", null)).toMatchObject({ kind: "rejection", code: null, stack: null });
  });

  it("says the kind of device roughly", () => {
    expect(deviceOf(390, true)).toBe("phone");
    expect(deviceOf(820, true)).toBe("tablet");
    expect(deviceOf(1440, false)).toBe("desktop");
  });

  it("sends at most five per browser session, also without storage", () => {
    const store = new Map<string, string>();
    const s = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
    const sent = Array.from({ length: 8 }, () => takeSlot(s)).filter(Boolean).length;
    expect(sent).toBe(MAX_PER_SESSION);
    const broken = { getItem: () => { throw new Error("blocked"); }, setItem: () => undefined };
    expect(Array.from({ length: 8 }, () => takeSlot(broken)).filter(Boolean).length).toBe(MAX_PER_SESSION);
  });
});

describe("the DOM hint of a hydration mismatch: tags and test ids, nothing else", () => {
  it("says what React took out and put in, net: a part rendered again the same cancels out", () => {
    const removed = ["div#match-head", "span#score", "p#kickoff", "li#row", "li#row"];
    const added = ["div#match-head", "span#score", "div#kickoff", "li#row"];
    expect(domHint(removed, added)).toBe("-p#kickoff,li#row|+div#kickoff");
    expect(domHint(["a#x"], ["a#x"])).toBeNull();
    // anything that is not a mark (a space, page text) is never sent
    expect(domHint(["p#a"], ["div#mia probst"])).toBeNull();
  });

  it("knows a hydration mismatch by React's number or, in a development build, its words", () => {
    expect(isHydration({ code: 418, message: "Minified React error #418" })).toBe(true);
    expect(isHydration({ code: null, message: "Hydration failed because the server rendered HTML didn't match" })).toBe(true);
    expect(isHydration({ code: 310, message: "Minified React error #310" })).toBe(false);
  });

  it("marks elements by tag and test id only, lower case, and skips ids that are not code constants", () => {
    const el = (tag: string, id: string | null) => ({ tagName: tag.toUpperCase(), getAttribute: () => id }) as unknown as Element;
    expect(markOf(el("div", "Match-Head"))).toBe("div#match-head");
    expect(markOf(el("span", "Mia Probst"))).toBeNull();
    expect(markOf(el("span", null))).toBeNull();
  });
});
