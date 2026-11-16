import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import api from "../../../apps/api/src/handball_api/services/drills.json";
import { DRILLS } from "./drills";

// The API lists the library together with the club's own drills (GET .../teams/{id}/drills) and
// suggests drills for the training tips, so it keeps a copy of DRILLS. After a change here, write
// the copy again: WRITE_DRILLS=1 pnpm --filter @handball/tactics test
const COPY = fileURLToPath(new URL("../../../apps/api/src/handball_api/services/drills.json", import.meta.url));

describe("drill library in the API", () => {
  it("is the same as DRILLS", () => {
    if (process.env.WRITE_DRILLS) writeFileSync(COPY, JSON.stringify(DRILLS, null, 2) + "\n");
    else expect(api).toEqual(JSON.parse(JSON.stringify(DRILLS)));
  });
});
