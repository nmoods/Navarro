import { expect, test } from "@playwright/test";

const email = `e2e-${Date.now()}@example.com`;
const password = "E2e-Strong-pass-1";

test.describe.configure({ mode: "serial" });

test("register, sign out and sign back in", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Turn any idea into a cinematic story." })).toBeVisible();
  await page.getByRole("link", { name: "Create account" }).click();
  await page.getByLabel("Your name").fill("E2E Creator");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "New video" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /Welcome back/ })).toBeVisible();
});

test("create, edit, regenerate, render, preview and download a video", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /Welcome back/ })).toBeVisible();

  // Wizard
  await page.goto("/create");
  await page.getByLabel("What is the video about?").fill("The lost Roanoke colony");
  await page.getByRole("button", { name: "30 seconds" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /Write the storyboard/ }).click();

  // Storyboard generated (script + storyboard)
  await expect(page.getByRole("button", { name: /^1\./ }).first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("button", { name: "Export video" })).toBeEnabled({ timeout: 60_000 }); // story job settled
  await page.getByRole("tab", { name: "Script" }).click();
  await expect(page.getByText("Hook Lab")).toBeVisible();
  await page.getByRole("tab", { name: "Scenes" }).click();

  // Edit a scene's narration and camera
  const narration = page.getByLabel("Narration");
  await narration.fill("A brand new opening line written in the editor.");
  await page.getByRole("button", { name: "Save narration" }).click();
  await expect(page.getByText("Saved")).toBeVisible();

  // Regenerate only this scene's image
  await page.getByRole("button", { name: "New image" }).click();
  await expect(page.getByText("Regenerating this scene")).toBeVisible();
  await expect(page.getByRole("button", { name: "Export video" })).toBeEnabled({ timeout: 60_000 });

  // Draft preview render
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText("Preview ready")).toBeVisible({ timeout: 180_000 });
  const video = page.locator("video");
  await expect(video).toBeVisible();
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.readyState), { timeout: 30_000 }).toBeGreaterThan(0);

  // Final export and download the MP4
  await page.getByRole("button", { name: "Export video" }).click();
  await expect(page.getByText("Video exported")).toBeVisible({ timeout: 180_000 });
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "MP4" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.mp4$/);
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(chunk as Buffer);
  const file = Buffer.concat(chunks);
  expect(file.subarray(4, 8).toString()).toBe("ftyp");
  expect(file.length).toBeGreaterThan(50_000);

  // Edit again and re-export: only the changed scene is rebuilt
  await page.getByLabel("Narration").fill("A second edit after the first export.");
  await page.getByRole("button", { name: "Save narration" }).click();
  await expect(page.getByText("You’ve made changes since this render.")).toBeVisible();
  await page.getByRole("button", { name: "Export video" }).click();
  await expect(page.getByText("Video exported")).toBeVisible({ timeout: 180_000 });
});
