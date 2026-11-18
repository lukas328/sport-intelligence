import { describe, expect, it } from "vitest";
import { pickEscape } from "./use-escape";

/** a tiny stand-in for elements: `contains` along a parent chain */
function node(parent: Node | null = null): Node {
  const n: Node = { parent, contains: (o: Node | null) => { for (let x = o; x; x = x.parent) if (x === n) return true; return false; } } as Node;
  return n;
}
interface Node {
  parent: Node | null;
  contains: (o: Node | null) => boolean;
}
const as = (n: Node | null) => n as unknown as Element;

describe("Escape closes one inline panel (A15)", () => {
  it("the panel around the focus, the innermost first", () => {
    const outer = node();
    const inner = node(outer);
    const focus = node(inner);
    expect(pickEscape(as(focus), [{ el: as(inner) }, { el: as(outer) }], null)).toBe(0);
    expect(pickEscape(as(focus), [{ el: as(outer) }, { el: as(inner) }], null)).toBe(1);
  });

  it("without a panel around the focus: the one opened last", () => {
    const a = node();
    const b = node();
    expect(pickEscape(as(node()), [{ el: as(a) }, { el: as(b) }], null)).toBe(1);
    expect(pickEscape(null, [{ el: null }], null)).toBe(0);
    expect(pickEscape(null, [], null)).toBeNull();
  });

  it("an open «Mehr» around the focus before the panel it sits in, never before an inner panel", () => {
    const panel = node();
    const details = node(panel);
    const focus = node(details);
    expect(pickEscape(as(focus), [{ el: as(panel) }], as(details))).toBe("details");
    expect(pickEscape(as(focus), [], as(details))).toBe("details");
    const inside = node(details);
    const f2 = node(inside);
    // the focus sits in a panel inside the «Mehr»: the panel first
    expect(pickEscape(as(f2), [{ el: as(inside) }], as(details))).toBe(0);
  });
});
