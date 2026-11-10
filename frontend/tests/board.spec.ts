import { expect, test, type Locator, type Page } from "@playwright/test";

const columns = (page: Page) => page.locator('[data-testid^="column-"]');
const cards = (page: Page) => page.locator('[data-testid^="card-"]');

async function startDrag(page: Page, card: Locator) {
  await card.scrollIntoViewIfNeeded();
  const box = await card.boundingBox();
  if (!box) throw new Error("Card has no bounding box");
  await page.mouse.move(box.x + 20, box.y + 20);
  await page.mouse.down();
  await page.mouse.move(box.x + 30, box.y + 20, { steps: 3 });
  await expect(page.locator("article")).toHaveCount(9);
}

async function dropOn(page: Page, target: Locator) {
  const box = await target.boundingBox();
  if (!box) throw new Error("Drop target has no bounding box");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, {
    steps: 20,
  });
  await page.mouse.up();
  await expect(page.locator("article")).toHaveCount(8);
}

test("loads and reloads with working assets, fonts, and no browser errors", async ({ page }, testInfo) => {
  const errors: string[] = [];
  const fonts: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("requestfailed", (request) => errors.push(request.url()));
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    if (response.url().includes(".woff2")) fonts.push(response.url());
  });

  await page.goto("/");
  await expect(page).toHaveTitle("Kanban Studio");
  await expect(page.getByRole("heading", { name: "Kanban Studio", exact: true })).toBeVisible();
  await expect(columns(page)).toHaveCount(5);
  await expect(cards(page)).toHaveCount(8);
  await page.evaluate(() => document.fonts.ready);
  expect(fonts.length).toBeGreaterThanOrEqual(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("board.png"), fullPage: true });
  await page.reload();
  await expect(cards(page)).toHaveCount(8);
  await page.evaluate(() => document.fonts.ready);
  expect(errors).toEqual([]);
});

test("renames a column and updates its summary", async ({ page }) => {
  await page.goto("/");
  await columns(page).first().getByRole("textbox", { name: "Column title" }).fill("Ready to start");
  await expect(page.locator("header").getByText("Ready to start", { exact: true })).toBeVisible();
});

test("adds and removes a card", async ({ page }) => {
  await page.goto("/");
  const column = columns(page).first();
  await column.getByRole("button", { name: "Add a card", exact: true }).click();
  await column.getByPlaceholder("Card title").fill("Playwright card");
  await column.getByPlaceholder("Details").fill("Added through the browser.");
  await column.getByRole("button", { name: "Add card", exact: true }).click();
  await expect(column.getByText("Playwright card", { exact: true })).toBeVisible();
  await expect(cards(page)).toHaveCount(9);
  await column.getByRole("button", { name: "Delete Playwright card", exact: true }).click();
  await expect(column.getByText("Playwright card", { exact: true })).toHaveCount(0);
  await expect(cards(page)).toHaveCount(8);
});

test("cancels a new card without changing the board", async ({ page }) => {
  await page.goto("/");
  const column = columns(page).first();
  await column.getByRole("button", { name: "Add a card", exact: true }).click();
  await column.getByPlaceholder("Card title").fill("Discard this draft");
  await column.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(cards(page)).toHaveCount(8);
  await column.getByRole("button", { name: "Add a card", exact: true }).click();
  await expect(column.getByPlaceholder("Card title")).toHaveValue("");
});

test("long text fits and column title focus is visible", async ({ page }) => {
  await page.goto("/");
  const column = columns(page).first();
  const title = column.getByRole("textbox", { name: "Column title" });
  await title.fill("LongColumnName".repeat(10));
  await expect(title).toHaveCSS("outline-style", "solid");
  await column.getByRole("button", { name: "Add a card", exact: true }).click();
  await column.getByPlaceholder("Card title").fill("LongCardTitle".repeat(15));
  await column.getByPlaceholder("Details").fill("LongDetails".repeat(30));
  await column.getByRole("button", { name: "Add card", exact: true }).click();
  const overflowing = await column.evaluate((element) =>
    [element, ...element.querySelectorAll("article")].some((item) => item.scrollWidth > item.clientWidth)
  );
  expect(overflowing).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("FastAPI health remains reachable alongside the exported site", async ({ request }) => {
  test.skip(!process.env.PLAYWRIGHT_BASE_URL, "Requires the FastAPI-served site");
  const response = await request.get("/api/health");
  expect(response.ok()).toBe(true);
  expect(await response.json()).toEqual({ status: "ok", message: "Hello from FastAPI." });
  expect((await request.get("/_next/static/missing.js")).status()).toBe(404);
});

test.describe("pointer drag and drop", () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "narrow-chromium", "Pointer drag targets are exercised in the desktop layout");
    await page.goto("/");
  });

  test("moves a card between columns", async ({ page }) => {
    await startDrag(page, page.getByTestId("card-card-1"));
    await dropOn(page, page.getByTestId("column-col-review"));
    await expect(page.getByTestId("column-col-review").getByTestId("card-card-1")).toBeVisible();
    await expect(page.getByTestId("column-col-backlog").locator("article")).toHaveCount(1);
  });

  test("reorders cards in the same column", async ({ page }) => {
    await startDrag(page, page.getByTestId("card-card-2"));
    await dropOn(page, page.getByTestId("card-card-1"));
    await expect(page.getByTestId("column-col-backlog").locator("h4")).toHaveText([
      "Gather customer signals", "Align roadmap themes",
    ]);
  });

  test("drops a card into an empty column", async ({ page }) => {
    const target = page.getByTestId("column-col-review");
    await target.getByRole("button", { name: "Delete QA micro-interactions", exact: true }).click();
    await expect(target.getByText("Drop a card here")).toBeVisible();
    const card = page.getByTestId("card-card-1");
    await card.hover();
    await page.mouse.down();
    const source = await card.boundingBox();
    if (!source) throw new Error("Card has no bounding box");
    await page.mouse.move(source.x + 20, source.y + 20, { steps: 4 });
    const box = await target.getByText("Drop a card here").boundingBox();
    if (!box) throw new Error("Empty column has no bounding box");
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 20 });
    await page.mouse.up();
    await expect(target.getByTestId("card-card-1")).toBeVisible();
    await expect(target.getByText("Drop a card here")).toHaveCount(0);
    await expect(cards(page)).toHaveCount(7);
  });

  test("Escape removes the drag preview and preserves card order", async ({ page }) => {
    await startDrag(page, page.getByTestId("card-card-1"));
    await page.mouse.move(700, 650, { steps: 12 });
    await page.keyboard.press("Escape");
    await expect(page.locator("article")).toHaveCount(8);
    await page.mouse.up();
    await expect(page.getByTestId("column-col-backlog").locator("h4")).toHaveText([
      "Align roadmap themes", "Gather customer signals",
    ]);
  });
});
