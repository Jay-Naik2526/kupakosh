import { test, expect } from "@playwright/test";

// Toggle EN/हिं on three screens and confirm the UI chrome actually switches to Hindi,
// without breaking layout (≤ 3 zones) or throwing console errors (SPEC.md §11.3, §11.4).
const SCREENS = ["/", "/offsets", "/wiki"];

for (const path of SCREENS) {
  test(`screen ${path}: EN/हिं toggle shows Hindi, no console errors, ≤ 3 zones`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto(path);
    await page.waitForLoadState("load");
    await page.waitForTimeout(1500);

    // Default language is English: the file-board line and footer must be visible as-is.
    await expect(page.getByText("Prototype for Oil India Limited · SIH 2026")).toBeVisible();
    await expect(page.getByText(/Decision support only/)).toBeVisible();

    // Toggle to Hindi.
    await page.getByRole("button", { name: "Toggle language" }).click();
    await page.waitForTimeout(300);

    // The file-board line and footer should now read in Hindi.
    await expect(page.getByText("ऑयल इंडिया लिमिटेड हेतु प्रोटोटाइप · SIH 2026")).toBeVisible();
    await expect(page.getByText(/केवल निर्णय सहायता/)).toBeVisible();

    // The active binder tab's heading should switch to its Hindi label.
    const heading = page.locator("h1.h-title");
    await expect(heading).toBeVisible();
    const headingText = await heading.textContent();
    expect(headingText ?? "").toMatch(/[ऀ-ॿ]/); // contains Devanagari

    // Layout must still respect the ≤ 3 zones rule after the toggle.
    const zones = await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll("main section[aria-label], main aside[aria-label]"));
      return all.filter((el) => !el.parentElement?.closest("section[aria-label], aside[aria-label]")).map((el) => el.getAttribute("aria-label"));
    });
    expect(zones.length, `zones: ${zones.join(", ")}`).toBeLessThanOrEqual(3);

    // Toggle back to English so state doesn't leak into other tests via localStorage.
    await page.getByRole("button", { name: "Toggle language" }).click();
    await page.waitForTimeout(300);
    await expect(page.getByText("Prototype for Oil India Limited · SIH 2026")).toBeVisible();

    expect(errors, errors.join("\n")).toEqual([]);
  });
}
