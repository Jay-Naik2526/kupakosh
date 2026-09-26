import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const SCREENS = ["/", "/offsets", "/wiki", "/fixes", "/mudwindow", "/checker", "/copilot", "/brief", "/accuracy"];

for (const path of SCREENS) {
  test(`screen ${path}: loads, no console errors, ≤ 3 zones, AA contrast`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(path);
    // map tiles keep the network busy on some screens, so wait for the API calls instead of network idle
    await page.waitForLoadState("load");
    await page.waitForTimeout(2500);
    await expect(page.getByText("Prototype for Oil India Limited · SIH 2026")).toBeVisible();
    await expect(page.getByText(/Decision support only/)).toBeVisible();
    // zones = outermost labelled sections/asides inside the sheet
    const zones = await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll("main section[aria-label], main aside[aria-label]"));
      return all.filter((el) => !el.parentElement?.closest("section[aria-label], aside[aria-label]")).map((el) => el.getAttribute("aria-label"));
    });
    expect(zones.length, `zones: ${zones.join(", ")}`).toBeLessThanOrEqual(3);
    const axe = await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze();
    const bad = axe.violations.flatMap((v) => v.nodes.map((n) => `${n.target.join(" ")} — ${n.any[0]?.message ?? ""}`));
    expect(bad, bad.slice(0, 8).join("\n")).toEqual([]);
    expect(errors, errors.join("\n")).toEqual([]);
  });
}

test("component gallery renders every component", async ({ page }) => {
  await page.goto("/dev/components");
  await page.waitForLoadState("networkidle");
  for (const name of ["Stamp", "NoticeSlip", "LithologyColumn", "SourceFootnote", "Register", "NotingSheet", "EmptyState", "CountryFilter", "Drawer"]) {
    await expect(page.getByRole("region", { name: new RegExp(name) })).toBeVisible();
  }
});

test("country filter narrows the ledger", async ({ page }) => {
  await page.goto("/fixes");
  await page.waitForLoadState("networkidle");
  const group = page.getByRole("group", { name: "country filter" });
  await group.getByRole("button", { name: /^All$/ }).click();
  const all = await page.getByText(/\d+ episodes · \d+ with a stated outcome/).textContent();
  await group.getByRole("button", { name: /^USA/ }).click();
  await expect(page.getByText(/\d+ episodes · \d+ with a stated outcome/)).not.toHaveText(all ?? "");
  await group.getByRole("button", { name: /^All$/ }).click();
});
