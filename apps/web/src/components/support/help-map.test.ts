import { describe, expect, it } from "vitest";
import { helpSlug, helpUrl } from "./help-map";

describe("context help", () => {
  it("maps screens to articles", () => {
    expect(helpSlug("/app/o/presentations/p/present")).toBe("praesentation");
    expect(helpSlug("/app/o/teams/t/matches")).toBe("video-hochladen");
    expect(helpSlug("/app/o/matches/m")).toBe("analyse-lesen");
    expect(helpSlug("/app/o")).toBe("erste-schritte");
    expect(helpUrl("https://handball-ai.ch/hilfe", "fr", "/app/o/consents")).toBe("https://handball-ai.ch/fr/hilfe/einwilligungen");
  });
});
