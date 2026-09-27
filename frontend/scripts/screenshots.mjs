// Deck screenshots of the running app (make api + make web). Usage: node scripts/screenshots.mjs
import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";

const BASE = process.env.KK_URL ?? "http://localhost:3000";
const OUT = fileURLToPath(new URL("../../docs/screenshots/", import.meta.url));
const b = await chromium.launch();
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
await page.getByRole("button", { name: /Map view/i }).click().catch(() => console.log("no map toggle"));
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
await goSafe("/map", "10-map", 5000);
await goSafe("/subsurface", "11-subsurface", 5000);
await goSafe("/analogs", "12-analogs", 4000);
await goSafe("/hindsight", "13-hindsight", 4000);

await b.close();
