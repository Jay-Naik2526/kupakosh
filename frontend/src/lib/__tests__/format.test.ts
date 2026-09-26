import { describe, expect, it } from "vitest";
import { m, num, pct, ppg, pretty } from "../format";

describe("format — unknown is never shown as 0", () => {
  it("depths", () => { expect(m(null)).toBe("unknown"); expect(m(undefined)).toBe("unknown"); expect(m(1234.4)).toBe("1,234 m"); });
  it("numbers", () => { expect(num(null)).toBe("unknown"); expect(num(0)).toBe("0"); });
  it("mud weight", () => { expect(ppg(null)).toBe("—"); expect(ppg(9.5)).toBe("9.50"); });
  it("percent", () => { expect(pct(null)).not.toBe("0%"); });
  it("formation names", () => { expect(pretty(null)).toBe("unknown"); expect(pretty("HUGIN FM")).toBe("Hugin Fm"); });
});
