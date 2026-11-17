import { describe, expect, it } from "vitest";
import { validityMessage } from "./form-validity";

const ok = { valid: true, valueMissing: false, typeMismatch: false, tooShort: false, tooLong: false, rangeUnderflow: false, rangeOverflow: false, stepMismatch: false, patternMismatch: false, badInput: false };
const bad = (state: Partial<typeof ok>) => ({ ...ok, valid: false, ...state });

describe("validityMessage", () => {
  it("is null for a valid field", () => {
    expect(validityMessage({ validity: ok })).toBeNull();
  });

  it("names a missing value first", () => {
    expect(validityMessage({ validity: bad({ valueMissing: true, typeMismatch: true }), type: "email" })).toEqual({ key: "valueMissing" });
  });

  it("tells e-mail and web addresses apart", () => {
    expect(validityMessage({ validity: bad({ typeMismatch: true }), type: "email" })?.key).toBe("typeMismatchEmail");
    expect(validityMessage({ validity: bad({ typeMismatch: true }), type: "url" })?.key).toBe("typeMismatchUrl");
  });

  it("carries the limits", () => {
    expect(validityMessage({ validity: bad({ tooShort: true }), minLength: 8 })).toEqual({ key: "tooShort", values: { n: 8 } });
    expect(validityMessage({ validity: bad({ rangeOverflow: true }), max: "99" })).toEqual({ key: "rangeOverflow", values: { max: "99" } });
  });

  it("has a general word for anything else", () => {
    expect(validityMessage({ validity: bad({}) })?.key).toBe("invalid");
  });
});
