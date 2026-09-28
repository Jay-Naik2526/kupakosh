// Deck screenshots of the running app (make api + make web). Usage: node scripts/screenshots.mjs
import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";

const BASE = process.env.KK_URL ?? "http://localhost:3000";
const OUT = fileURLToPath(new URL("../../docs/screenshots/", import.meta.url));
// SwiftShader WebGL so the 3D canvas renders in headless Chromium.
const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await b.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
const shot = async (name) => { await page.screenshot({ path: OUT + name + ".png" }); console.log("saved", name); };
const go = async (path, wait = 3000) => { await page.goto(BASE + path); await page.waitForLoadState("load"); await page.waitForTimeout(wait); };
// A page owned by another agent may not exist yet mid-build — don't let that fail the whole run.
const goSafe = async (path, name, wait = 3000) => {
  try { await go(path, wait); await shot(name); } catch (e) { console.log(`skipped ${name} (${path}):`, e.message?.split("\n")[0]); }
};

// 00 Home (new v2 shell landing page)
await goSafe("/", "00-home", 3000);

// 01 Well Room (was "Command"): start the REPLAY of 16B and wait for a look-ahead notice
await go("/command");
await page.getByRole("button", { name: /Start replay/ }).click();
await page.waitForSelector("text=/range .*evidence/i", { timeout: 90000 }).catch(() => console.log("no notice yet"));
await page.waitForTimeout(4000);
await shot("01-command-replay");
await page.getByRole("button", { name: /Pause/ }).click().catch(() => {});

for (const [path, name, wait] of [["/offsets", "02-offsets", 5000], ["/wiki?page=formations%2Fbasin-fill-alluvium", "03-wiki", 3000],
  ["/fixes", "04-fixes", 3000], ["/mudwindow", "05-mudwindow", 4000], ["/checker", "06-checker", 3000], ["/brief", "08-brief", 4000],
  ["/accuracy", "09-accuracy", 3000]]) { await go(path, wait); await shot(name); }

// 02 Offsets map view
await go("/offsets", 4000);
await page.getByRole("tab", { name: /Map view/ }).click().catch(() => page.getByRole("button", { name: /^Map$/ }).click()).catch(() => console.log("no map tab"));
await page.waitForTimeout(5000);
await shot("02-offsets-map");

// 07 Copilot: one cited answer and one refusal
await go("/copilot");
for (const q of ["What worked against stuck pipe in the Draupne Formation?", "What is the unconfined compressive strength of the Hugin Formation?"]) {
  await page.getByRole("textbox", { name: "question" }).fill(q); await page.getByRole("button", { name: /^Ask$/ }).click();
  await page.waitForSelector(`text=${q.slice(0, 30)}`); await page.waitForTimeout(2500);
}
await shot("07-copilot");

// New v2 screens (owned by other agents building in parallel; skip gracefully if not shipped yet)
await goSafe("/map", "10-map", 9000);
await goSafe("/subsurface", "11-subsurface", 12000);
// 11b: the same 3D room on a Norwegian well (15/9-19 S, id from the live DB) — 41 wells, 40+ real formations.
const nor = await page.evaluate(async () => (await (await fetch("/api/wells?q=15/9-19%20S&limit=1")).json())[0]?.id).catch(() => null);
if (nor) {
  await page.evaluate((id) => localStorage.setItem("kk.wellId", JSON.stringify(id)), nor);
  await goSafe("/subsurface", "11b-subsurface-norway", 14000);
  await page.evaluate(() => localStorage.removeItem("kk.wellId"));
}
// 10b: map on satellite imagery
await go("/map", 6000);
await page.getByRole("button", { name: "Satellite" }).click().catch(() => {});
await page.waitForTimeout(6000);
await shot("10b-map-satellite");
await goSafe("/analogs", "12-analogs", 4000);
await goSafe("/hindsight", "13-hindsight", 4000);

// 14: Home in dark mode
await page.evaluate(() => localStorage.setItem("kk.theme", JSON.stringify("dark")));
await goSafe("/", "14-home-dark", 3000);
await page.evaluate(() => localStorage.setItem("kk.theme", JSON.stringify("light")));

await b.close();
