import { describe, expect, it } from "vitest";
import api from "../../../apps/api/src/handball_api/services/drills.json";
import { DRILLS } from "./drills";

// The API lists the library together with the club's own drills (GET .../teams/{id}/drills), so it
// keeps a copy of DRILLS. After a change here, write the copy again from the repository root:
// node --experimental-strip-types -e "import('./packages/tactics/src/drills.ts').then(m =>
//   process.stdout.write(JSON.stringify(m.DRILLS, null, 2) + '\n'))" > apps/api/src/handball_api/services/drills.json
describe("drill library in the API", () => {
  it("is the same as DRILLS", () => {
    expect(api).toEqual(JSON.parse(JSON.stringify(DRILLS)));
  });
});
