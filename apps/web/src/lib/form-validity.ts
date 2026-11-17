/**
 * Form checks in the app's language (review R10): the browser writes «Please fill out this field»
 * in its own language, which is not the coach's. Which message a field gets, from its validity
 * state; `null` while it is valid.
 */
export type ValidityKey =
  | "valueMissing"
  | "typeMismatchEmail"
  | "typeMismatchUrl"
  | "typeMismatch"
  | "tooShort"
  | "tooLong"
  | "rangeUnderflow"
  | "rangeOverflow"
  | "stepMismatch"
  | "patternMismatch"
  | "badInput"
  | "invalid";

export interface ValidityMessage {
  key: ValidityKey;
  values?: Record<string, string | number>;
}

type Field = {
  validity: Pick<
    ValidityState,
    | "valid"
    | "valueMissing"
    | "typeMismatch"
    | "tooShort"
    | "tooLong"
    | "rangeUnderflow"
    | "rangeOverflow"
    | "stepMismatch"
    | "patternMismatch"
    | "badInput"
  >;
  type?: string;
  minLength?: number;
  maxLength?: number;
  min?: string;
  max?: string;
};

export function validityMessage(el: Field): ValidityMessage | null {
  const v = el.validity;
  if (v.valid) return null;
  if (v.valueMissing) return { key: "valueMissing" };
  if (v.badInput) return { key: "badInput" };
  if (v.typeMismatch)
    return {
      key:
        el.type === "email"
          ? "typeMismatchEmail"
          : el.type === "url"
            ? "typeMismatchUrl"
            : "typeMismatch",
    };
  if (v.tooShort) return { key: "tooShort", values: { n: el.minLength ?? 0 } };
  if (v.tooLong) return { key: "tooLong", values: { n: el.maxLength ?? 0 } };
  if (v.rangeUnderflow) return { key: "rangeUnderflow", values: { min: el.min ?? "" } };
  if (v.rangeOverflow) return { key: "rangeOverflow", values: { max: el.max ?? "" } };
  if (v.stepMismatch) return { key: "stepMismatch" };
  if (v.patternMismatch) return { key: "patternMismatch" };
  return { key: "invalid" };
}
