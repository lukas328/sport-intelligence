import { expect, test } from "@playwright/test";

// Web vitals budgets (BRIEF 7.3): LCP < 2.5 s, CLS < 0.1, measured with 4x CPU throttling
// (close to Lighthouse's mobile profile). Network is local, so this guards rendering cost.
for (const path of ["/", "/login", "/register"]) {
  test(`web vitals ${path}`, async ({ page, browserName }, info) => {
    test.skip(browserName !== "chromium" || info.project.name !== "chromium", "CDP throttling");
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await page.addInitScript(() => {
      const w = window as unknown as { __lcp: number; __cls: number };
      w.__lcp = 0;
      w.__cls = 0;
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) w.__lcp = e.startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });
      new PerformanceObserver((list) => {
        for (const e of list.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[])
          if (!e.hadRecentInput) w.__cls += e.value;
      }).observe({ type: "layout-shift", buffered: true });
    });
    await page.goto(path, { waitUntil: "networkidle" });
    await page.waitForTimeout(500);
    const { lcp, cls } = await page.evaluate(() => {
      const w = window as unknown as { __lcp: number; __cls: number };
      return { lcp: w.__lcp, cls: w.__cls };
    });
    console.log(`${path}: LCP ${Math.round(lcp)} ms, CLS ${cls.toFixed(3)}`);
    expect(lcp).toBeGreaterThan(0);
    expect(lcp).toBeLessThan(2500);
    expect(cls).toBeLessThan(0.1);
  });
}
