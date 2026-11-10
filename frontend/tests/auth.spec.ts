import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("user");
  await page.getByLabel("Password", { exact: true }).fill("password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
}

test.afterEach(async ({ context }) => {
  await context.request.delete("/api/session");
});

test("fresh visits show sign-in without board content", async ({ page, request }, testInfo) => {
  const html = await (await request.get("/")).text();
  expect(html).not.toContain("Align roadmap themes");
  expect((await request.get("/api/session")).status()).toBe(401);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
  await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("type", "password");
  await page.evaluate(() => document.fonts.ready);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("sign-in.png"), fullPage: true });
});

test("rejects wrong credentials and then accepts the MVP credentials", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("user");
  await page.getByLabel("Password", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Invalid username or password.");
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
  await page.getByLabel("Password", { exact: true }).fill("password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByTestId("card-card-1")).toBeVisible();
});

test("reload restores the session using an HttpOnly cookie", async ({ page, context }) => {
  await signIn(page);
  const cookie = (await context.cookies()).find((item) => item.name === "kanban_session");
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  expect(await page.evaluate(() => document.cookie)).not.toContain("kanban_session");
  await page.reload();
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
  await expect(page.getByTestId("card-card-1")).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toHaveCount(0);
});

test("sign-out revokes the token and returning does not expose board state", async ({ page, context }) => {
  await signIn(page);
  const token = (await context.cookies()).find((item) => item.name === "kanban_session")!.value;
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
  expect((await context.request.get("/api/session", {
    headers: { Cookie: `kanban_session=${token}` },
  })).status()).toBe(401);
  await page.goto("/missing");
  await page.goBack();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
  await page.reload();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
});

test("a revoked session clears the board when the window regains focus", async ({ page, context }) => {
  await signIn(page);
  await context.request.delete("/api/session");
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
});

test("session expiry is detected by the periodic check", async ({ page, context }) => {
  await page.clock.install();
  await signIn(page);
  await context.request.delete("/api/session");
  await page.clock.fastForward(60_000);
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
});

test("failed session lookup offers retry without revealing the board", async ({ page }) => {
  await page.route("**/api/session", (route) => route.fulfill({ status: 503 }));
  await page.goto("/");
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Unable to check your session. Please try again.");
  await expect(page.getByTestId("card-card-1")).toHaveCount(0);
  await page.unroute("**/api/session");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
});

test("failed sign-in and sign-out requests are recoverable", async ({ page }) => {
  await page.route("**/api/session", async (route) => {
    if (route.request().method() === "POST") await route.fulfill({ status: 503 });
    else await route.continue();
  });
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("user");
  await page.getByLabel("Password", { exact: true }).fill("password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Unable to sign in. Please try again.");
  await expect(page.getByLabel("Username", { exact: true })).toHaveValue("user");
  await page.unroute("**/api/session");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByTestId("card-card-1")).toBeVisible();
  await page.route("**/api/session", async (route) => {
    if (route.request().method() === "DELETE") await route.fulfill({ status: 503 });
    else await route.continue();
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Unable to sign out. Please try again.");
  await expect(page.getByTestId("card-card-1")).toBeVisible();
  await page.unroute("**/api/session");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
});
