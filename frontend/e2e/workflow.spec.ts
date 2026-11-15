import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs/promises";

test("real audio → editable chart → saved project → printable export", async ({
  page,
}) => {
  const errors: string[] = [],
    external: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/*", (route) => {
    if (
      !route.request().url().startsWith("http://127.0.0.1:8765") &&
      !route.request().url().startsWith("blob:")
    ) {
      external.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your music, on the page." }),
  ).toBeVisible();
  await page.screenshot({ path: "../tmp/library.png", fullPage: true });
  await page
    .getByRole("button", { name: "New transcription", exact: true })
    .last()
    .click();
  await page
    .getByLabel("Audio recording")
    .setInputFiles(path.resolve("../tmp/sunday-sketch.wav"));
  await page.getByLabel("Song title", { exact: true }).fill("Sunday Sketch");
  await page
    .getByLabel("Composer / artist")
    .fill("Mulec original fixture · CC0");
  await page.getByRole("button", { name: "Analyze recording" }).click();
  await expect(
    page.getByRole("heading", { name: "Sunday Sketch", exact: true }).first(),
  ).toBeVisible({ timeout: 120000 });
  await page.getByRole("button", { name: /^Bar 1:/ }).click();
  const chord = page
    .getByRole("textbox", { name: "Chord symbol", exact: true })
    .first();
  await chord.fill("Bbmaj7/F");
  await chord.press("Tab");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Saved on this computer",
  );
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Bbmaj7/F",
  );
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).not.toContainText(
    "Bbmaj7/F",
  );
  await page.getByRole("button", { name: "Redo", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Bbmaj7/F",
  );
  await page
    .getByRole("combobox", { name: "Instrument part" })
    .selectOption("bb");
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Cmaj7/G",
  );
  await page
    .getByRole("combobox", { name: "Instrument part" })
    .selectOption("concert");
  await page.getByRole("button", { name: /^Bar 1:/ }).click();
  await page.getByText("Melody notes (0)", { exact: true }).click();
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await page.getByRole("button", { name: "Close bar editor" }).click();
  await page.screenshot({ path: "../tmp/workspace.png", fullPage: true });
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Printable chord chart · PDF" })
    .click();
  await (await download).saveAs("../tmp/mulec-chart.pdf");
  await page.getByRole("button", { name: "Lead sheet", exact: true }).click();
  await expect(page.locator(".notation svg").first()).toBeVisible({
    timeout: 30000,
  });
  await page.screenshot({ path: "../tmp/lead-sheet.png", fullPage: true });
  await page.getByRole("button", { name: "Chord chart", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../tmp/mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.reload();
  await page
    .getByRole("button", { name: /Sunday Sketch/ })
    .first()
    .click();
  await expect(page.getByRole("button", { name: /^Bar 1:/ })).toContainText(
    "Bbmaj7/F",
  );
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
  expect(
    (await fs.readFile("../tmp/mulec-chart.pdf")).subarray(0, 4).toString(),
  ).toBe("%PDF");
});
