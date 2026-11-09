import { parse } from "@handball/client-core";
import { describe, expect, it } from "vitest";
import { pathFor } from "./routes";

const ORG = "11111111-1111-1111-1111-111111111111";
const ID = "22222222-2222-2222-2222-222222222222";

describe("deep links into the app", () => {
  it("maps notification links to screens", () => {
    expect(pathFor(parse(`/app/${ORG}/matches/${ID}?t=1200`))).toBe(`/clip/${ID}?t=1200`);
    expect(pathFor(parse(`handball://clip/${ID}?t=5`))).toBe(`/clip/${ID}?t=5`);
    expect(pathFor(parse(`/app/${ORG}/assignments`))).toBe("/assignments");
    expect(pathFor(parse(`/app/${ORG}/presentations/${ID}/present`))).toBe(`/remote/${ID}`);
    expect(pathFor(parse("https://evil.example/x"))).toBe("/feed");
  });
});
